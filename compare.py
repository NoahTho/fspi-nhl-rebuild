import pandas as pd, numpy as np, sys
tg=pd.read_csv('team_games.csv'); o=pd.read_csv('official_20261011.csv').set_index('team')
d=pd.read_csv('index_daily.csv'); cur=d[(d.season==20262027)&(d.date=='2026-10-11')].set_index('team')['index']
diff=(cur-o['official']).round(2)
print('maxabs',diff.abs().max(),'exact',(diff.abs()<0.01).sum(),'within2',(diff.abs()<=2).sum())
if len(sys.argv)>1:
    s=tg[tg.season==20262027]
    cols=[c for c in s.columns if c.startswith('n_')]
    N=s.groupby('team')[cols].sum().loc[diff.index]
    N=N.loc[:,N.std()>0]
    res=[]
    for c in N:
        x=N[c].values; b=np.linalg.lstsq(np.c_[x],diff.values,rcond=None)[0][0]
        res.append((round((diff.values-b*x).std(),2),c,round(b,3)))
    for r in sorted(res)[:10]: print(r)
    print(diff.sort_values().to_string())
