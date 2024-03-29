"""
需要添加當資料加入時可以更新而不是全部重寫
"""
import pandas as pd
import os
from tqdm import tqdm
from datetime import date

# Windows is awesome
# NOT_IN_CP950 = {"喆": "吉吉"}


class Preprocesser:
    def __init__(self):
        # 分檔案用
        self.company_pd = pd.read_csv("data/company_list.csv", index_col=False)
        # 排版用
        self.df_col = ["日期","證券代號", "證券名稱", "產業別", "成交股數", "成交筆數", "成交金額", "開盤價", "最高價", "最低價", "收盤價", "漲跌(+/-)",
          "漲跌價差", "最後揭示買價", "最後揭示買量", "最後揭示賣價", "最後揭示賣量", "本益比", "外陸資買進股數(不含外資自營商)",
          "外陸資賣出股數(不含外資自營商)", "外陸資買賣超股數(不含外資自營商)", "外資自營商買進股數", "外資自營商賣出股數",
          "外資自營商買賣超股數", "投信買進股數", "投信賣出股數", "投信買賣超股數", "自營商買賣超股數", "自營商買進股數(自行買賣)",
          "自營商賣出股數(自行買賣)", "自營商買賣超股數(自行買賣)", "自營商買進股數(避險)", "自營商賣出股數(避險)",
          "自營商買賣超股數(避險)", "三大法人買賣超股數"]

    def init_company_file(self):
        """
        將以日期分的資料轉為以公司分
        :return:
        """
        log_name = "data/log/" + date.today().strftime("%Y%m%d") + ".csv"
        if os.path.isfile(log_name):
            with open(log_name, "a") as write_file:
                write_file.write("Init t2p,,\n")

        tqdm_sf = tqdm(os.listdir("data/stock"))

        # load stock and tii information
        info_list = self._load_time_data(tqdm_sf)

        # write data according to company
        self._write_company_data(info_list)

    def update_company_file(self, start_date: int, end_date: int, company=None):
        """
        更新現有資料
        :param start_date: 從哪天開始做起
        :param end_date: 做到哪一天(如果你選的時間是周末或股市修盤則會順延至最近的開盤日)
        :param company: 需要更新公司(代號)，如果為 None 則全做
        :return: 
        """
        # log 分一下段
        log_name = "data/log/" + date.today().strftime("%Y%m%d") + ".csv"
        if os.path.isfile(log_name):
            with open(log_name, "a") as write_file:
                write_file.write("update t2c,,\n")
        else:
            with open(log_name, "w") as write_file:
                write_file.write("update t2c,,\n")

        # 只取需要的時間
        file_list = os.listdir("data/stock")
        starting_file, ending_file = 0, 0
        start_flag = False
        for fid, f in enumerate(file_list):
            if int(f[:-4]) >= start_date and start_flag is False:
                starting_file = fid
                start_flag = True

            if int(f[:-4]) >= end_date or fid == len(file_list) - 1:  # 預防使用者輸入超過的值
                ending_file = fid
                break

        file_list = file_list[starting_file:ending_file + 1]
        print(file_list)
        tqdm_sf = tqdm(file_list)

        # load stock and tii information
        info_list = self._load_time_data(tqdm_sf)

        # 只取需要的company
        if company is None:
            self._write_company_data(info_list)
        else:
            mask = self.company_pd["證券代號"].isin(company)
            update_companies = self.company_pd.loc[mask]
            self._write_company_data(info_list, update_companies)

    def _remove_empty(self, df):
        """
        Remove Unname column and NAN row
        :param df: Want remove data frame
        :return: New data frame
        """
        # 去掉空col, row
        # df.set_index('類型', inplace=True)
        drop_col = []
        for col in df.columns:
            if "Unnamed" in col:
                drop_col.append(col)
        df.drop(columns=drop_col, inplace=True)
        df.dropna(how="all", inplace=True)
        return df

    def _load_time_data(self, tqdm_sf):
        """
        讀取由時間組成的資料，即data 中的stock, tii_company 資料
        :param tqdm_sf: stock, tiicompany 中要使用的資料檔名
        :return: 時間資料 info_list
        """
        if type(tqdm_sf) == list:
            tqdm_sf = tqdm(tqdm_sf)

        # load stock and tii information
        info_list = []
        for stock_file in tqdm_sf:
            tqdm_sf.set_description(stock_file)

            # 收盤資訊
            each_day_stock_pd = pd.read_csv("data/stock/" + stock_file, encoding="cp950")
            each_day_stock_pd = self._remove_empty(each_day_stock_pd)
            each_day_stock_pd.set_index("證券代號")
            stock_mask = (each_day_stock_pd["證券代號"].isin(self.company_pd["證券代號"].tolist()))

            # 三大法人資訊
            each_day_tii_pd = pd.read_csv("data/tii_company/" + stock_file, encoding="cp950")
            each_day_tii_pd = self._remove_empty(each_day_tii_pd)
            each_day_tii_pd.set_index("證券代號")
            tii_mask = (each_day_tii_pd["證券代號"].isin(self.company_pd["證券代號"].tolist()))

            info_list.append({"file_name": stock_file, "stock": each_day_stock_pd.loc[stock_mask],
                              "tii": each_day_tii_pd.loc[tii_mask]})

        return info_list

    def _write_company_data(self, info_list, update_companies=None, init=False):
        """
        將時間資料轉成各個company
        :param info_list: 時間資料，由 _load_time_data 生成
        :param update_companies: 如果是None 則 update_companies = self.company_df，否則根據update_companies 來寫入需要更新的公司
        :param init: True: flush data
        :return: data/company
        """
        if update_companies is None:
            update_companies = self.company_pd

        for company_index, update_companies in update_companies.iterrows():
            # if company_index <= 830:
            #     continue
            print(update_companies["證券代號"], update_companies["證券名稱"], company_index, "/", len(self.company_pd))
            company_stock_pd = pd.DataFrame(columns=self.df_col)
            append_dict = {}

            for info in tqdm(info_list):
                try:
                    # Extract data
                    company_stock_info = info["stock"].loc[info["stock"]["證券代號"] == update_companies["證券代號"]].iloc[0]
                    try:
                        company_tii_info = info["tii"].loc[info["tii"]["證券代號"] == update_companies["證券代號"]].iloc[0]
                    except:
                        company_tii_info = pd.Series(0, index=info["tii"].columns)

                    if not company_stock_info.empty:
                        # if init is False:
                        #
                        # 寫入
                        append_dict.update(company_stock_info.to_dict())
                        append_dict.update(company_tii_info.to_dict())

                        append_dict["證券代號"] = update_companies["證券代號"]
                        append_dict["證券名稱"] = company_stock_info["證券名稱"]
                        append_dict["產業別"] = update_companies["產業別"]
                        append_dict["日期"] = info["file_name"][:8]
                        company_stock_pd = company_stock_pd.append(append_dict, ignore_index=True)

                except:
                    print("!!!", update_companies["證券名稱"], info["file_name"][:8], " 的靈壓消失了")
                    # 寫log
                    # log_name = "data/log/" + date.today().strftime("%Y%m%d") + ".csv"
                    # if os.path.isfile(log_name):
                    #     with open(log_name, "a") as write_file:
                    #         write_file.write("no data," + company["證券代號"] + "," + info["file_name"][:8] + "\n")
                    # else:
                    #     with open(log_name, "w") as write_file:
                    #         write_file.write("error,info_name,date\n")
                    #         write_file.write("Preprocesser,,\n")
                    #         write_file.write("no data," + company["證券代號"] + "," + info["file_name"][:8] + "\n")
                    # del log_name

                    # tqdm_sf.close()
                    # break
            if init is False:
                original_data = pd.read_csv("data/company/" + update_companies["證券代號"] + ".csv", encoding="cp950")
                original_data = original_data.dropna()
                original_data = original_data.append(company_stock_pd)  # add new element
                original_data["日期"] = original_data["日期"].astype(int)
                original_data = original_data.drop_duplicates("日期", keep="first")  # drop same element
                original_data = original_data.sort_values(by="日期", axis=0)
                original_data.to_csv("data/company/" + update_companies["證券代號"] + ".csv", encoding="cp950", index=False)
            else:
                company_stock_pd.to_csv("data/company/" + update_companies["證券代號"] + ".csv", encoding="cp950", index=False)


if __name__ == "__main__":
    print("  ")

    preprocesser = Preprocesser()
    preprocesser.update_company_file(start_date=20191020, end_date=20191023, company=["2492"])
    # for file in os.listdir("data/stock"):
    #     print(file)

    # print("元大台灣50" in list(df2["證券名稱"]))
    # print(self.company_pd.head())