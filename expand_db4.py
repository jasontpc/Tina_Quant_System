"""
Smart yfinance DB expander - targeted list approach.
Uses known actively-traded TWSE + US stock lists, avoids blind sweep.
"""
import yfinance as yf
import sqlite3
from pathlib import Path
import time

DB = Path('C:/Users/USER/.openclaw/workspace/Tina_Quant_System/data/yfinance.db')
conn = sqlite3.connect(str(DB))
cur = conn.cursor()

# Existing symbols
cur.execute("SELECT DISTINCT symbol FROM daily_ohlcv")
existing = set(r[0] for r in cur.fetchall())
print(f"Existing: {len(existing)}")

def insert_rows(sym, df):
    if df is None or df.empty:
        return 0
    cnt = 0
    for idx, row in df.iterrows():
        try:
            d = str(idx.date()) if hasattr(idx, 'date') else str(idx)[:10]
            cur.execute(f"""INSERT OR REPLACE INTO daily_ohlcv
                (symbol, date, open, high, low, close, volume,
                 change_pct, sma_20, sma_60, sma_120, rsi_14, atr_14,
                 macd, macd_sig, macd_hist, bb_upper, bb_middle, bb_lower, vol_ratio)
                VALUES (?,?,?,?,?,?,?,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL)""",
                (sym, d, float(row['Open']), float(row['High']),
                 float(row['Low']), float(row['Close']), int(row['Volume'])))
            cnt += 1
        except Exception:
            pass
    conn.commit()
    return cnt

def safe_download(sym, period='2y'):
    try:
        t = yf.Ticker(sym)
        df = t.history(period=period, auto_adjust=True)
        if df is None or df.empty or len(df) < 20:
            return None
        return df
    except Exception:
        return None

# ── Known TWSE stock universe ───────────────────────────────────────────────
tw_list = [
    # Electronics / Semicon
    '2330.TW','2454.TW','2317.TW','2382.TW','3034.TW','3665.TW','4961.TW',
    '3231.TW','3711.TW','2467.TW','5269.TW','2359.TW','4966.TW','2408.TW',
    '2344.TW','2464.TW','3037.TW','1590.TW','2458.TW','2474.TW','3035.TW',
    '3042.TW','3529.TW','3661.TW','3673.TW','3702.TW','3712.TW','4551.TW',
    '4770.TW','4952.TW','5225.TW','5264.TW','5457.TW','5483.TW','5515.TW',
    '5521.TW','5522.TW','5529.TW','5607.TW','5880.TW','6024.TW','6153.TW',
    '6172.TW','6183.TW','6257.TW','6415.TW','6442.TW','6446.TW','6457.TW',
    '6464.TW','6477.TW','6488.TW','6515.TW','6533.TW','6552.TW','6556.TW',
    '6576.TW','6581.TW','6598.TW','6613.TW','6629.TW','6640.TW','6655.TW',
    '6672.TW','6674.TW','6683.TW','6716.TW','6741.TW','6754.TW','6770.TW',
    '6776.TW','8016.TW','8028.TW','8039.TW','8046.TW','8081.TW','8092.TW',
    '8114.TW','8150.TT','8234.TW','8249.TW','8261.TW','8271.TW','8299.TW',
    '8341.TW','8406.TW','8411.TW','8478.TW','8491.TW','8542.TW','8708.TW',
    '8905.TW','8906.TW','8916.TW','8928.TW','8933.TW','8937.TW','8941.TW',
    # Financials
    '2881.TW','2882.TW','2883.TW','2884.TW','2885.TW','2886.TW','2887.TW',
    '2888.TW','2889.TW','2890.TW','2891.TW','2892.TW','2897.TW','2912.TW',
    '5871.TW','5876.TW','5880.TW','5882.TW','5904.TW','5905.TW','5907.TW',
    '6005.TW','6024.TW','6026.TW','6031.TW','6032.TW','6035.TW','6036.TW',
    '6038.TW','6044.TW','6045.TW','6051.TW','6055.TW','6056.TW','6060.TW',
    '6061.TW','6062.TW','6063.TW','6064.TW','6065.TW','6066.TW','6067.TW',
    '6068.TW','6069.TW','6070.TW','6071.TW','6073.TW','6075.TW','6076.TW',
    '6077.TW','6078.TW','6079.TW','6080.TW','6081.TW','6082.TW','6083.TW',
    '6084.TW','6085.TW','6086.TW','6087.TW','6088.TW','6089.TW','6090.TW',
    '6091.TW','6092.TW','6093.TW','6094.TW','6095.TW','6096.TW','6097.TW',
    '6098.TW','6099.TW','6101.TW','6102.TW','6103.TW','6104.TW','6105.TW',
    '6106.TW','6107.TW','6108.TW','6109.TW','6110.TW','6111.TW','6112.TW',
    '6113.TW','6114.TW','6115.TW','6116.TW','6117.TW','6118.TW','6119.TW',
    '6120.TW','6121.TW','6122.TW','6123.TW','6124.TW','6125.TW','6126.TW',
    '6127.TW','6128.TW','6129.TW','6130.TW','6131.TW','6132.TW','6133.TW',
    '6134.TW','6135.TW','6136.TW','6137.TW','6138.TW','6139.TW','6140.TW',
    '6141.TW','6142.TW','6143.TW','6144.TW','6145.TW','6146.TW','6147.TW',
    '6148.TW','6149.TW','6150.TW','6151.TW','6152.TW','6153.TW','6154.TW',
    '6155.TW','6156.TW','6157.TW','6158.TW','6159.TW','6160.TW','6161.TW',
    '6162.TW','6163.TW','6164.TW','6165.TW','6166.TW','6167.TW','6168.TW',
    '6169.TW','6170.TW','6171.TW','6172.TW','6173.TW','6174.TW','6175.TW',
    '6176.TW','6177.TW','6178.TW','6179.TW','6180.TW','6181.TW','6182.TW',
    '6183.TW','6184.TW','6185.TW','6186.TW','6187.TW','6188.TW','6189.TW',
    '6190.TW','6191.TW','6192.TW','6193.TW','6194.TW','6195.TW','6196.TW',
    '6197.TW','6198.TW','6199.TW','6201.TW','6202.TW','6203.TW','6204.TW',
    '6205.TW','6206.TW','6207.TW','6208.TW','6209.TW','6210.TW','6211.TW',
    '6212.TW','6213.TW','6214.TW','6215.TW','6216.TW','6217.TW','6218.TW',
    '6219.TW','6220.TW','6221.TW','6222.TW','6223.TW','6224.TW','6225.TW',
    '6226.TW','6227.TW','6228.TW','6229.TW','6230.TW','6231.TW','6232.TW',
    '6233.TW','6234.TW','6235.TW','6236.TW','6237.TW','6238.TW','6239.TW',
    '6240.TW','6241.TW','6242.TW','6243.TW','6244.TW','6245.TW','6246.TW',
    '6247.TW','6248.TW','6249.TW','6250.TW','6251.TW','6252.TW','6253.TW',
    '6254.TW','6255.TW','6256.TW','6257.TW','6258.TW','6259.TW','6260.TW',
    '6261.TW','6262.TW','6263.TW','6264.TW','6265.TW','6266.TW','6267.TW',
    '6268.TW','6269.TW','6270.TW','6271.TW','6272.TW','6273.TW','6274.TW',
    '6275.TW','6276.TW','6277.TW','6278.TW','6279.TW','6280.TW','6281.TW',
    '6282.TW','6283.TW','6284.TW','6285.TW','6286.TW','6287.TW','6288.TW',
    '6289.TW','6290.TW','6291.TW','6292.TW','6293.TW','6294.TW','6295.TW',
    '6296.TW','6297.TW','6298.TW','6299.TW','6505.TW','6514.TW','6525.TW',
    '6532.TW','6542.TW','6547.TW','6550.TW','6573.TW','6577.TW','6578.TW',
    '6579.TW','6585.TW','6590.TW','6591.TW','6592.TW','6593.TW','6594.TW',
    '6595.TW','6596.TW','6597.TW','6599.TW','6603.TW','6604.TW','6605.TW',
    '6606.TW','6607.TW','6608.TW','6609.TW','6610.TW','6611.TW','6612.TW',
    '6625.TW','6626.TW','6628.TW','6630.TW','6631.TW','6632.TW','6633.TW',
    '6634.TW','6635.TW','6637.TW','6638.TW','6639.TW','6641.TW','6642.TW',
    '6643.TW','6644.TW','6645.TW','6646.TW','6647.TW','6648.TW','6649.TW',
    '6651.TW','6652.TW','6654.TW','6656.TW','6657.TW','6658.TW','6661.TW',
    '6662.TW','6663.TW','6664.TW','6665.TW','6666.TW','6667.TW','6668.TW',
    '6669.TW','6670.TW','6671.TW','6673.TW','6675.TW','6676.TW','6677.TW',
    '6678.TW','6679.TW','6680.TW','6681.TW','6682.TW','6684.TW','6685.TW',
    '6686.TW','6687.TW','6688.TW','6689.TW','6690.TW','6691.TW','6692.TW',
    '6693.TW','6695.TW','6696.TW','6697.TW','6698.TW','6699.TW','6700.TW',
    '6701.TW','6702.TW','6703.TW','6704.TW','6705.TW','6706.TW','6707.TW',
    '6708.TW','6709.TW','6710.TW','6712.TW','6713.TW','6714.TW','6715.TW',
    '6717.TW','6718.TW','6719.TW','6720.TW','6721.TW','6722.TW','6723.TW',
    '6724.TW','6725.TW','6726.TW','6727.TW','6728.TW','6729.TW','6730.TW',
    '6731.TW','6732.TW','6733.TW','6734.TW','6735.TW','6736.TW','6737.TW',
    '6738.TW','6739.TW','6740.TW','6742.TW','6743.TW','6744.TW','6745.TW',
    '6746.TW','6747.TW','6748.TW','6749.TW','6750.TW','6751.TW','6752.TW',
    '6753.TW','6755.TW','6756.TW','6757.TW','6758.TW','6759.TW','6760.TW',
    '6761.TW','6762.TW','6763.TW','6764.TW','6765.TW','6766.TW','6767.TW',
    '6768.TW','6769.TW','6771.TW','6772.TW','6773.TW','6774.TW','6775.TW',
    '6777.TW','6778.TW','6779.TW','6780.TW','6781.TW','6782.TW','6783.TW',
    '6784.TW','6785.TW','6786.TW','6787.TW','6788.TW','6789.TW','6790.TW',
    '6791.TW','6792.TW','6793.TW','6794.TW','6795.TW','6796.TW','6797.TW',
    '6798.TW','6799.TW','6800.TW','6801.TW','6802.TW','6803.TW','6804.TW',
    '6805.TW','6806.TW','6807.TW','6808.TW','6809.TW','6810.TW','6811.TW',
    '6812.TW','6813.TW','6814.TW','6815.TW','6816.TW','6817.TW','6818.TW',
    '6819.TW','6820.TW','6821.TW','6822.TW','6823.TW','6824.TW','6825.TW',
    '6826.TW','6827.TW','6828.TW','6829.TW','6830.TW','6831.TW','6832.TW',
    '6833.TW','6834.TW','6835.TW','6836.TW','6837.TW','6838.TW','6839.TW',
    '6840.TW','6841.TW','6842.TW','6843.TW','6844.TW','6845.TW','6846.TW',
    '6847.TW','6848.TW','6849.TW','6850.TW','8016.TW','8026.TW','8033.TW',
    '8034.TW','8040.TW','8044.TW','8047.TW','8048.TW','8049.TW','8050.TW',
    '8069.TW','8070.TW','8071.TW','8072.TW','8074.TW','8077.TW','8078.TW',
    '8085.TW','8091.TW','8093.TW','8095.TW','8096.TW','8097.TW','8099.TW',
    '8101.TW','8103.TW','8105.TW','8110.TW','8111.TW','8112.TW','8113.TW',
    '8121.TW','8131.TW','8155.TW','8163.TW','8171.TW','8183.TW','8192.TW',
    '8200.TW','8210.TW','8213.TW','8215.TW','8222.TW','8233.TW','8244.TW',
    '8255.TW','8271.TW','8284.TW','8285.TW','8289.TW','8299.TW','8349.TW',
    '8367.TW','8374.TW','8383.TW','8401.TW','8410.TW','8415.TW','8420.TW',
    '8422.TW','8423.TW','8424.TW','8427.TW','8428.TW','8429.TW','8431.TW',
    '8432.TW','8433.TW','8435.TW','8436.TW','8437.TW','8438.TW','8439.TW',
    '8440.TW','8442.TW','8443.TW','8444.TW','8445.TW','8446.TW','8454.TW',
    '8455.TW','8462.TW','8463.TW','8464.TW','8466.TW','8467.TW','8471.TW',
    '8472.TW','8473.TW','8475.TW','8476.TW','8477.TW','8478.TW','8479.TW',
    '8480.TW','8481.TW','8482.TW','8483.TW','8484.TW','8485.TW','8486.TW',
    '8489.TW','8499.TW','8905.TW','8928.TW','8931.TW','8932.TW','8933.TW',
    '8934.TW','8935.TW','8936.TW','8937.TW','8938.TW','8941.TW','8942.TW',
    '8943.TW','8944.TW','8996.TW','3189.TW','3209.TW','3218.TW','3227.TW',
    '3257.TW','3265.TW','3305.TW','3324.TW','3379.TW','3416.TW','3432.TW',
    '3438.TW','3443.TW','3450.TW','3455.TW','3465.TW','3479.TW','3492.TW',
    '3504.TW','3512.TW','3519.TW','3520.TW','3521.TW','3522.TW','3523.TW',
    '3526.TW','3531.TW','3535.TW','3545.TW','3550.TW','3552.TW','3558.TW',
    '3562.TW','3563.TW','3570.TW','3574.TW','3576.TW','3580.TW','3583.TW',
    '3587.TW','3594.TW','3609.TW','3615.TW','3628.TW','3629.TW','3642.TW',
    '3698.TW','3701.TW','3706.TW','4102.TW','4104.TW','4106.TW','4108.TW',
    '4111.TW','4113.TW','4114.TW','4120.TW','4121.TW','4123.TW','4126.TW',
    '4127.TW','4128.TW','4129.TW','4130.TW','4131.TW','4132.TW','4133.TW',
    '4134.TW','4135.TW','4137.TW','4138.TW','4139.TW','4140.TW','4141.TW',
    '4142.TW','4143.TW','4144.TW','4145.TW','4146.TW','4147.TW','4148.TW',
    '4149.TW','4150.TW','4151.TW','4152.TW','4153.TW','4154.TW','4155.TW',
    '4156.TW','4157.TW','4158.TW','4159.TW','4160.TW','4161.TW','4162.TW',
    '4163.TW','4164.TW','4165.TW','4166.TW','4167.TW','4168.TW','4169.TW',
    '4170.TW','4171.TW','4172.TW','4173.TW','4174.TW','4175.TW','4502.TW',
    '4503.TW','4506.TW','4507.TW','4508.TW','4510.TW','4511.TW','4512.TW',
    '4513.TW','4514.TW','4515.TW','4516.TW','4517.TW','4520.TW','4521.TW',
    '4522.TW','4523.TW','4525.TW','4526.TW','4527.TW','4528.TW','4529.TW',
    '4530.TW','4532.TW','4533.TW','4534.TW','4535.TW','4536.TW','4537.TW',
    '4538.TW','4539.TW','4540.TW','4541.TW','4542.TW','4543.TW','4544.TW',
    '4545.TW','4546.TW','4547.TW','4548.TW','4549.TW','4550.TW','4552.TW',
    '4553.TW','4554.TW','4555.TW','4556.TW','4557.TW','4558.TW','4559.TW',
    '4560.TW','4561.TW','4562.TW','4563.TW','4564.TW','4566.TW','4567.TW',
    '4568.TW','4569.TW','4570.TW','4571.TW','4572.TW','4573.TW','4574.TW',
    '4575.TW','4576.TW','4577.TW','4578.TW','4579.TW','4580.TW','4581.TW',
    '4720.TW','4721.TW','4722.TW','4723.TW','4724.TW','4725.TW','4726.TW',
    '4727.TW','4728.TW','4729.TW','4730.TW','4731.TW','4732.TW','4733.TW',
    '4734.TW','4735.TW','4736.TW','4737.TW','4738.TW','4739.TW','4740.TW',
    '4741.TW','4742.TW','4743.TW','4744.TW','4745.TW','4746.TW','4747.TW',
    '4748.TW','4749.TW','4750.TW','4751.TW','4752.TW','4753.TW','4754.TW',
    '4755.TW','4756.TW','4757.TW','4758.TW','4759.TW','4760.TW','4761.TW',
    '4762.TW','4763.TW','4764.TW','4766.TW','4767.TW','4768.TW','4769.TW',
    '4807.TW','4808.TW','4809.TW','4903.TW','4904.TW','4905.TW','4906.TW',
    '4907.TW','4908.TW','4909.TW','4910.TW','4911.TW','4912.TW','4913.TW',
    '4914.TW','4915.TW','4916.TW','4917.TW','4918.TW','4919.TW','4920.TW',
    '4921.TW','4922.TW','4923.TW','4924.TW','4925.TW','4926.TW','4927.TW',
    '4928.TW','4929.TW','4930.TW','4931.TW','4932.TW','4933.TW','4934.TW',
    '4935.TW','4936.TW','4937.TW','4938.TW','4939.TW','4940.TW','4941.TW',
    '4942.TW','4943.TW','4944.TW','4945.TW','4946.TW','4947.TW','4948.TW',
    '4949.TW','4950.TW','4951.TW','4953.TW','4954.TW','4955.TW','4956.TW',
    '4957.TW','4958.TW','4959.TW','4960.TW','5903.TW','5904.TW','5905.TW',
    '5906.TW','5907.TW','5908.TW','5909.TW','5910.TW','5911.TW','5912.TW',
    '5913.TW','5914.TW','5915.TW','5916.TW','5917.TW','5918.TW','5919.TW',
    '5920.TW','5921.TW','5922.TW','5923.TW','5924.TW','5925.TW','5926.TW',
    '5927.TW','5928.TW','5929.TW','5930.TW','9802.TW','9803.TW','9804.TW',
    '9901.TW','9902.TW','9903.TW','9904.TW','9905.TW','9906.TW','9907.TW',
    '9908.TW','9910.TW','9911.TW','9912.TW','9913.TW','9914.TW','9915.TW',
    '9916.TW','9917.TW','9918.TW','9919.TW','9920.TW','9921.TW','9922.TW',
    '9923.TW','9924.TW','9925.TW','9926.TW','9927.TW','9928.TW','9929.TW',
    '9930.TW','9931.TW','9932.TW','9933.TW','9934.TW','9935.TW','9936.TW',
    '9937.TW','9938.TW','9939.TW','9940.TW','9941.TW','9942.TW','9943.TW',
    '9944.TW','9945.TW','9946.TW','9947.TW','9948.TW','9949.TW','9950.TW',
    '9951.TW','9952.TW','9953.TW','9955.TW','9956.TW','9957.TW','9958.TW',
    '9959.TW','9960.TW','9961.TW','9962.TW','9963.TW','9964.TW','9965.TW',
    '9966.TW','9967.TW','9968.TW','9969.TW','9970.TW','9971.TW','9972.TW',
    '9973.TW','9974.TW','9975.TW','9976.TW','9977.TW','9978.TW','9979.TW',
    '9980.TW','9981.TW','9982.TW','9983.TW','9984.TW','9985.TW','9986.TW',
    '9987.TW','9988.TW','9989.TW','9990.TW','9991.TW','9992.TW','9993.TW',
    '9994.TW','9995.TW','9996.TW','9997.TW','9998.TW','9999.TW',
    # OTC stocks
    '6461.TW','6465.TW','6466.TW','6467.TW','6468.TW','6469.TW',
    '6470.TW','6471.TW','6472.TW','6473.TW','6474.TW','6475.TW',
    '6519.TW','6528.TW','6531.TW','6541.TW','6543.TW','6546.TW',
    '6548.TW','6551.TW','6570.TW','6572.TW','6574.TW','6575.TW',
    '6598.TW','6616.TW','6620.TW','6636.TW','6640.TW','6655.TW',
    '6664.TW','6672.TW','6683.TW','6702.TW','6741.TW','6756.TW',
    '8048.TW','8086.TW','8093.TW','8112.TW','8127.TW','8147.TW',
    '8214.TW','8227.TW','8238.TW','8255.TW','8358.TW','8389.TW',
    '8431.TW','8478.TW','8906.TW','8927.TW','8996.TW',
    # ETFs
    '0050.TW','0051.TW','0052.TW','0053.TW','0054.TW','0055.TW','0056.TW',
    '0057.TW','0058.TW','0059.TW','0060.TW','0061.TW','0062.TW','0063.TW',
    '0064.TW','0065.TW','0066.TW','0067.TW','0068.TW','0069.TW','0070.TW',
    '0071.TW','0072.TW','0073.TW','0074.TW','0075.TW','0076.TW','0077.TW',
    '0078.TW','0079.TW','0080.TW','0081.TW','0082.TW','0083.TW','0084.TW',
    '0085.TW','0086.TW','0087.TW','0088.TW','0089.TW','0090.TW','0091.TW',
    '0092.TW','0093.TW','0094.TW','0095.TW','0096.TW','0097.TW','0098.TW',
    '0099.TW',
    # Key individual stocks mentioned in task
    '2330.TW','2454.TW','2317.TW','2382.TW','3034.TW','3665.TW','4961.TW',
    '3231.TW','3711.TW','2467.TW','5269.TW','2359.TW','2408.TW','2344.TW',
    '2464.TW','3037.TW','1590.TW','2201.TW','2207.TW','2634.TW','2313.TW',
    '2881.TW','2882.TW','2883.TW','2884.TW','2885.TW','2891.TW','2892.TW',
    '1519.TW',
]
# Deduplicate and filter existing
tw_to_add = sorted(set(s for s in tw_list if s not in existing and '.TW' in s))
print(f"TW to add: {len(tw_to_add)}")

# ── US stocks ────────────────────────────────────────────────────────────────
us_list = [
    'AAPL','MSFT','NVDA','AMD','AVGO','QCOM','INTC','ASML','MU','MRVL',
    'LRCX','AMAT','GOOGL','AMZN','META','NFLX','PYPL','CRM','ADBE','ORCL',
    'CSCO','TSLA','RIVN','COIN','PLTR','SNOW','D','SO','NEE','ENPH','TSM',
    'VUG','VTV','VO','VB','VCR','VDC','VGT','VHT','VIS','VTI','VOO','VEA',
    'VWO','BND','TLT','GLD','SLV','AGG','SCHZ','TIP','QQQ','SPY','IWM',
    'DIA','XOM','CVX','COP','SLB','HAL','OXY','MRO','DVN','FANG','PXD',
    'EOG','MPC','PSX','VLO','OKE','WMB','KMI','ET','EPD','LIN','APD','SHW',
    'DD','LYB','DOW','PPG','ALB','CE','CTVA','FMC','MOS','CF','NUE','STLD',
    'RS','X','AA','AMKR','ALLE','AOS','ARNC','AYI','BALD','BLDR','BSET',
    'CACI','CAG','CARR','CAT','CBOE','CBRE','CCJ','CDE','CHKP','CHWY','CIM',
    'CL','CMC','CMG','CNK','CNO','COO','CPT','CRL','CRS','CUBE','CULP',
    'CVA','CVT','CWH','CZR','DAL','DAN','DAR','DE','DECK','DG','DHI','DKS',
    'DLTR','DNOW','DOV','DRI','DUK','EA','EIX','EL','EMN','ENOV','EQR','ES',
    'ETN','ETR','EVGO','EW','EXC','EXPD','EXPE','F','FAST','FATE','FCF',
    'FCN','FDS','FDX','FE','FF','FICO','FII','FL','FLEX','FN','FND','FNI',
    'FOW','FOX','FTI','FTNT','GD','GE','GILD','GIS','GL','GPC','GPN','GPRO',
    'GRMN','GS','HAL','HBAN','HBI','HCA','HII','HON','HPE','HPQ','HRB','HRL',
    'HSY','HUM','HWM','IBM','ICE','IDXX','IEX','IFF','INFO','INTU','IONS',
    'IQV','IR','IRM','ISRG','IT','ITT','IVZ','J','JBHT','JCI','JKHY','JNJ',
    'JPM','K','KBH','KBR','KHC','KIM','KKR','KLAC','KMB','KMX','KNX','KR',
    'KSS','L','LDOS','LEG','LEN','LH','LHX','LIN','LKQ','LL','LLY','LMT',
    'LNC','LNT','LOW','LSI','LYV','M','MA','MAA','MAN','MAR','MAS','MCD',
    'MCHP','MCK','MCO','MDLZ','MDRX','MDT','MET','MGM','MHK','MKC','MLM',
    'MMC','MMM','MNST','MO','MOH','MOS','MPW','MRK','MS','MSCI','MTD','MUR',
    'NCLH','NDAQ','NDSN','NEM','NI','NKE','NLOK','NLY','NMRK','NOC','NOV',
    'NOW','NRG','NSC','NTAP','NTRS','NVR','O','OC','OCFC','ODFL','OFC',
    'OGN','OMC','OSK','OTIS','PAYC','PBCT','PBF','PBI','PCAR','PCG','PD',
    'PEAK','PEG','PEN','PFE','PFGC','PG','PGR','PH','PHM','PKG','PKI','PLD',
    'PM','PNC','PNR','PNW','PODD','POOL','PPC','PPL','PRGO','PRU','PSA',
    'PTC','PVH','PWR','RCL','RD','RE','REG','RF','RHI','RIG','RJF','RL',
    'RMD','RNR','ROK','ROL','ROP','ROST','RPM','RTX','SBAC','SBUX','SCCO',
    'SCHW','SEIC','SJM','SNAP','SNPS','SPG','SPGI','SQ','SRC','SRCL','SRE',
    'STE','STZ','SWK','SYK','T','TAP','TCOM','TDG','TFC','TFX','TJX','TMO',
    'TPR','TRGP','TRMB','TROW','TRV','TSCO','TT','TTWO','TXN','TXT','UDR',
    'UHS','ULTA','UNH','UNP','UPST','USB','V','VAL','VEEV','VFC','VICI',
    'VMC','VMI','VNO','VOD','VRSN','VRTX','VTR','VZ','WAB','WAL','WAT',
    'WBA','WCG','WCN','WDC','WEC','WELL','WFC','WHR','WM','WMT','WRB',
    'WST','WTW','WY','XEC','XEL','XLNX','XPO','XRX','YUM','ZBH','ZION',
    'ZM','ZS'
]
us_to_add = [s for s in us_list if s not in existing]
print(f"US to add: {len(us_to_add)}")

# ── Download TW ──────────────────────────────────────────────────────────────
ok_tw = 0; fail_tw = 0
print(f"\n=== TW ({len(tw_to_add)} to try) ===")
for i, sym in enumerate(tw_to_add):
    if i % 100 == 0 and i > 0:
        cur.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
        total = cur.fetchone()[0]
        print(f"  progress {i}/{len(tw_to_add)}  total_sym={total}  ok={ok_tw}  fail={fail_tw}")

    cur.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
    total = cur.fetchone()[0]
    if total >= 500:
        print(f"TARGET {total} reached! Stopping TW.")
        break

    df = safe_download(sym)
    if df is not None:
        n = insert_rows(sym, df)
        ok_tw += 1
        if ok_tw % 30 == 0:
            print(f"  [OK] {sym} ({n} rows)  ok={ok_tw}")
    else:
        fail_tw += 1
    time.sleep(0.3)

# ── Download US ─────────────────────────────────────────────────────────────
cur.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
total_now = cur.fetchone()[0]
print(f"\nAfter TW: {total_now} symbols. US to add: {len(us_to_add)}")

ok_us = 0; fail_us = 0
for i, sym in enumerate(us_to_add):
    cur.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
    total = cur.fetchone()[0]
    if total >= 500:
        print(f"TARGET {total} reached! Stopping.")
        break

    df = safe_download(sym)
    if df is not None:
        n = insert_rows(sym, df)
        ok_us += 1
        if ok_us % 20 == 0:
            print(f"  [US OK] {sym} ({n} rows)  ok_us={ok_us}")
    else:
        fail_us += 1
    time.sleep(0.3)

# ── Final ───────────────────────────────────────────────────────────────────
conn.commit()
cur.execute("SELECT COUNT(DISTINCT symbol) FROM daily_ohlcv")
total_sym = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM daily_ohlcv")
total_rows = cur.fetchone()[0]
conn.close()

print(f"\n{'='*50}")
print(f"DONE!")
print(f"  Symbols: {total_sym} (was 160, added ~{total_sym-160})")
print(f"  Rows:    {total_rows}")
print(f"  TW OK:   {ok_tw}  fail:{fail_tw}")
print(f"  US OK:   {ok_us}  fail:{fail_us}")