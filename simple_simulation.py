import datetime
import datetime as dt
import numpy as np
import pandas as pd

GROWTH_STAGE_LIST = ['seedling_stage', 'survival&jointing_stage', 'tillering_stage', 'reproductive_growth_stage',
                     'maturity_stage']


def get_growth_stage(method='gdd', **kwargs):
    if method == 'gdd':
        # 根据积温返回生育期,从播种开始计算
        acc_tmp = 0
        for k, v in kwargs.items():
            if k == 'acc_tmp':
                acc_tmp = float(v)
        if acc_tmp < 384:
            return GROWTH_STAGE_LIST[0]
        elif acc_tmp < 584:
            return GROWTH_STAGE_LIST[1]
        elif acc_tmp < 1206:
            return GROWTH_STAGE_LIST[2]
        elif acc_tmp < 1502:
            return GROWTH_STAGE_LIST[3]
        elif acc_tmp < 2102:
            return GROWTH_STAGE_LIST[4]
        else:
            return 'end'


def get_gdd(tmp):
    t_b = 10
    t_m = 40
    if tmp > t_m:
        tmp = t_m
    elif tmp < t_b:
        tmp = t_b
    return tmp - t_b


class Crop:
    def __init__(self, sd):
        self.acc_tmp = 0
        self.seeding_date = sd
        self.growth_stage = 'seedling_stage'

    def manual_update(self, pgs, dt):
        # 根据巡田结果更新作物生育期
        pass

    def daily_update(self, tmp):
        # 根据每日气温更新作物积温和生育期，返回当前生育期和积温
        self.acc_tmp += get_gdd(tmp)
        self.growth_stage = get_growth_stage(method='gdd', acc_tmp=self.acc_tmp)
        return self.acc_tmp, self.growth_stage

    def batch_update(self, tmp_list):
        # 批量更新积温
        pass


class CropManagement:
    GROWTH_STAGE_FARMING_ACTIVITIES = {'seedling_stage': ['ploughing', 'base_fert', 'transplanting'],
                                       'tillering_stage': ['tillering_fert', 'end_tillering_drying'],
                                       'reproductive_growth_stage': ['panicle_fert'],
                                       'maturity_stage': ['before_harvest_drying', 'harvest']}

    def __init__(self, seeding_date, init_date):
        self.crop = Crop(seeding_date)
        self.init_date = init_date
        self.update_date = init_date

        # 农事时间
        self.transplanting_date = ''


    def update_seedling_stage_fa(self, cdt, gddl, envs):
        flag_list = gddl >= 384
        trans_num = flag_list.index(True)
        if trans_num == 0:
            return ''
        trans_num_min = max(trans_num - 2, 1)
        trans_num_max = trans_num + 3
        trans_num_pre_list = envs.precipitation_forecast[trans_num_min:trans_num_max]
        min_pre_num = trans_num_pre_list.index(min(trans_num_pre_list))
        if min_pre_num >5:
            base_fert_min_pre_num =
        self.transplanting_date = cdt + dt.timedelta(days=min_pre_num)

    def daily_update(self, date, envs):
        date = dt.date(int(date.split('-')[0]), int(date.split('-')[1]), int(date.split('-')[2]))
        self.update_date = date
        crop_c_acc_tmp = self.crop.acc_tmp
        agg_gdd_list = [crop_c_acc_tmp + get_gdd(i) for i in envs.temperature_forecast]

    def get_status(self):
        print("播种更新状态：{0}，播种时间：{1} \n"
              "基肥更新状态：{2}，基肥时间：{3} \n"
              "移栽更新状态：{4}，移栽时间：{5}，距离播种天数：{13} \n"
              "分蘖肥更新状态：{6}，分蘖肥时间：{7}，距离移栽天数：{14} \n"
              "穗肥更新状态：{8}，穗肥时间：{9}，距离移栽天数：{15} \n"
              "收获更新状态：{10}，收获时间：{11}，距离移栽天数：{16} \n "
              "更新时间：{12}".format(str(self.seeding_status), str(self.seeding_date),
                                     str(self.base_fert_status), str(self.base_fert_date),
                                     str(self.transplanting_status), str(self.transplanting_date),
                                     str(self.tillering_fert_status), str(self.tillering_fert_date),
                                     str(self.panicle_fert_status), str(self.panicle_fert_date),
                                     str(self.harvesting_status), str(self.harvesting_date), str(self.update_date),
                                     str(self.transplanting_date - self.seeding_date),
                                     str(self.tillering_fert_date - self.transplanting_date),
                                     str(self.panicle_fert_date - self.transplanting_date),
                                     str(self.harvesting_date - self.transplanting_date)))


class EnvironmentState:
    def __init__(self):
        self.pre = 0
        self.tmp = 0
        self.precipitation_forecast = []
        self.temperature_forecast = []

    def update(self, cs,fs):
        self.pre = cs.precipitation
        self.tmp = cs.temperature
        self.precipitation_forecast = fs['precipitation_forecast']
        self.temperature_forecast = fs['temperature_forecast']


if __name__ == '__main__':
    weather_data = pd.read_csv('2020_weather.csv', index_col=0)
    weather_data.columns = ['date', 'temp', 'prec']
    test_env = EnvironmentState()
    test_crop = CropManagement(2020)
    for index, row in weather_data.iterrows():
        temp_date = row['date']
        temp_f_7d = weather_data.iloc[index + 1:index + 8, 1].values.tolist()
        prec_f_7d = weather_data.iloc[index + 1:index + 8, 2].values.tolist()
        test_env.update({"precipitation_forecast_7d": prec_f_7d, "temperature_forecast_7d": temp_f_7d})
        test_crop.update(temp_date, test_env)
