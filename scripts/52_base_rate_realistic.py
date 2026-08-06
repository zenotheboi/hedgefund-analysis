"""Realistic base rate from the PHASE MIX (not the 10% P1->approval figure).

We trade Phase 2 / Phase 3 / regulatory readouts. Their real-world success
rates are much higher than 10%, so the honest base rate for OUR universe is a
phase-weighted blend (~55%), close to the dataset's 68%. Recompute returns,
precision and (approx) CAGR at: dataset 68%, realistic ~56%, doomsday 10%.

CAGR uses a linear anchor: at 100% model the per-position return is W and the
portfolio makes $28.9M (29% CAGR) -> final ~= 10*(1 + k*mean_return).
"""
import json
W, L = 0.173, -0.138          # mean per-position return: long a winner / a loser (script 51)
K = (28.9/10 - 1) / W          # portfolio leverage factor anchored on the 100% case
ANCHOR = "100% model: +17.3%/position -> $28.9M / 29% CAGR"

# our dataset phase mix
mix = {"Phase 3": 139, "Phase 2": 106, "Regulatory": 75}
tot = sum(mix.values())
our_rate = {"Phase 3": 98/139, "Phase 2": 60/106, "Regulatory": 59/75}
real_rate = {"Phase 3": 0.58, "Phase 2": 0.32, "Regulatory": 0.87}   # industry (BIO/Informa)
blend = sum(mix[p]/tot * real_rate[p] for p in mix)
print("phase mix + success rates (ours vs real-world):")
for p in mix:
    print(f"  {p:11} {mix[p]:3} events ({mix[p]/tot*100:2.0f}%)  ours {our_rate[p]*100:2.0f}%  real ~{real_rate[p]*100:2.0f}%")
print(f"\ndataset blended success = {217/320*100:.0f}%   REALISTIC phase-weighted = {blend*100:.0f}%   (NOT 10%)\n")

def final_cagr(r):
    f = 10*(1 + K*r); c = (max(f,0.01)/10)**0.25 - 1 if f>0 else -1
    return f, c

print(f"{'base rate':>22} | {'no-model':>16} | {'90% model':>18} | {'80% model':>18}")
print("-"*84)
out={}
for label,p in [("dataset 68%",0.68),("REALISTIC ~56%",blend),("doomsday 10% (P1->appr)",0.10)]:
    row={}
    cells=[]
    # no-model
    r=p*W+(1-p)*L; f,c=final_cagr(r); cells.append(f"${f:4.1f}M/{c*100:+3.0f}%"); row["no_model"]={"final":f,"cagr":c}
    for a in [0.90,0.80]:
        prec=(p*a)/(p*a+(1-p)*(1-a)); r=prec*W+(1-prec)*L; f,c=final_cagr(r)
        cells.append(f"${f:4.1f}M/{c*100:+3.0f}% (prec {prec*100:.0f}%)"); row[f"m{int(a*100)}"]={"precision":prec,"final":f,"cagr":c}
    print(f"{label:>22} | {cells[0]:>16} | {cells[1]:>18} | {cells[2]:>18}")
    out[label]=row
json.dump({"blended_realistic":blend,"K":K,"table":out},open("data/processed/base_rate_realistic.json","w"),indent=2,default=float)
print(f"\nanchor: {ANCHOR}")
print("wrote data/processed/base_rate_realistic.json")
