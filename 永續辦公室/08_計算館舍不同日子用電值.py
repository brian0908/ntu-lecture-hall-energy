# -*- coding: utf-8 -*-
"""
Created on Mon Sep 18 08:44:57 2023

@author: fishball
"""

import pandas as pd
import numpy as np

list = pd.read_excel("C:\\Dropbox\\work\\01_Research\\18_用電 EUI\\02_穩定版程式\\00_data\\建物與電表對照_程式用.xlsx")
area=list['面積'].rename(list['建物編號'])
name=list['建物名稱'].rename(list['建物編號'])
df3=pd.DataFrame(name).join(pd.DataFrame(area))

id=name.index

result_ans=pd.read_excel("C:\\Dropbox\\work\\01_Research\\18_用電 EUI\\02_穩定版程式\\07_output\\Dayoff_NTUAS_ele_data.xlsx")
data=[]
out1=pd.DataFrame(data)
for id2 in id:
  bb_name=name[id2]
  bb_area=area[id2]
  for i in range(0,4):
    ans=result_ans[result_ans['Dayoff']== i ]
    nn=np.full((24), np.nan)

    s1=ans[(ans['hh']<= 6) & (ans['Temp']<=18.9)]
    s11=s1[id2].to_numpy()
    ele_cold_morning=s11[:][~np.isnan(s11[:])]

    s2=ans[(ans['hh']>= 12) & (ans['hh']<= 18)&  (ans['Temp']<=20.5)]
    s22=s2[id2].to_numpy()
    ele_cold_afternoon=s22[:][~np.isnan(s22[:])]

    s3=ans[(ans['hh']<= 6) & (ans['Temp']>=28.5)]
    s33=s3[id2].to_numpy()
    ele_hot_morning=s33[:][~np.isnan(s33[:])]

    s4=ans[(ans['hh']>= 12) & (ans['hh']<= 18)&  (ans['Temp']>=31.4)]
    s44=s4[id2].to_numpy()
    ele_hot_afternoon=s44[:][~np.isnan(s44[:])]

    ans1="nan"
    ans2="nan"
    ans3="nan"
    ans4="nan"

    if(len(ele_cold_morning)>1):
      ans1=round(np.percentile(ele_cold_morning,75))
    if(len(ele_cold_afternoon)>1):
      ans2=round(np.percentile(ele_cold_afternoon,75))
    if(len(ele_hot_morning)>1):
      ans3=round(np.percentile(ele_hot_morning,75))
    if(len(ele_hot_afternoon)>1):
      ans4=round(np.percentile(ele_hot_afternoon,75))

    print(id2,bb_name,':',i,':',ans1,',',ans2,',',ans3,',',ans4)
    exec(f"value_1_{i}=ans1")
    exec(f"value_2_{i}=ans2")
    exec(f"value_3_{i}=ans3")
    exec(f"value_4_{i}=ans4")

  morning=[value_1_0,value_1_1,value_1_2,value_1_3]
  afternoon=[value_2_0,value_2_1,value_2_2,value_2_3]
  morning.sort()
  afternoon.sort()
#計算不同時期用電差異
  output1=min(morning) #凌晨最低
  output2=min(afternoon) #下午最低
  output3=max(morning[1]-output1,0) #設備基本待機
  output4=max(min(value_3_0,value_3_2,value_3_3)-output1-output3,0) #設備待機暖季增量
  output6=max(min(value_2_3-output2-output3,value_2_0-output2-output3),0) #上班/研究用電
  output5=max(value_2_0-output2-output3-output6,0) #上課用電
  output8=max(value_4_3-output2-output3-output4-output6,0) #上班/研究空調用電
  output7=max(value_4_0-output2-output3-output4-output5-output6-output8,0) #上課空調用電
  print("凌晨最低=",output1," ,下午最低＝",output2," ,設備基本待機＝ +", output3," ,設備待機暖季增量＝ +", output4," ,上課設備用電＝ +", output5," ,上班/研究設備用電＝ +", output6," ,上課空調用電＝ +", output7," ,上班/研究空調用電＝ +", output8)
  #print("館舍基礎用電密度=",min(value_1_1,value_3_1)/bb_area," 空調 暖季增加用電= +", output7+output8 , "空調 增量用電密度= ", (output7+output8)/bb_area)
  print("館舍基礎用電:",min(value_1_1,value_1_0,value_3_0),"設備待機用電(+暖季):", output3+output4,"人員設備使用用電:",output5+output6,"人員空調使用用電:", output7+output8)
  #print("館舍基礎用電密度:",min(value_1_1,value_1_0,value_3_0)/bb_area,"設備待機用電密度(+暖季):", (output3+output4)/bb_area,"人員設備使用用電密度:",(output5+output6)/bb_area,"人員空調使用用電密度:", (output7+output8)/bb_area)
  #out=pd.DataFrame([id2,bb_name,bb_area,min(value_1_1,value_1_0,value_3_0),output3+output4,output5+output6,output7+output8,min(value_1_1,value_1_0,value_3_0)/bb_area,(output3+output4)/bb_area,(output5+output6)/bb_area,(output7+output8)/bb_area])
  #out1=pd.concat([out.T,out1],ignore_index=True,axis=0)

#out1.columns=["館舍ID","館舍名稱","館舍面積","館舍基礎用電","設備待機用電(+暖季)","人員設備使用用電","人員空調使用用電","館舍基礎用電密度","設備待機用電密度(+暖季)","人員設備使用用電密度","人員空調使用用電密度"]
#out1.to_excel("C:\\Dropbox\\work\\01_Research\\18_用電 EUI\\02_穩定版程式\\08_output\\館舍用電基礎值.xlsx")