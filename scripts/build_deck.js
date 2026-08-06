const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.defineLayout({ name: "W", width: 13.333, height: 7.5 }); p.layout = "W";
const R = "/Users/gigi/hedgefund-analysis/reports";
const NAVY="1E2761", INK="141B33", ICE="CADCFC", MINT="02C39A", RED="C0392F",
      MUTED="5B636E", LINE="E4E6EE", WHITE="FFFFFF", FAINT="8A919B", GOLD="E0A458";
const HF="Cambria", BF="Calibri", INKT="27313F";

function pageno(s,n){ s.addText(String(n).padStart(2,"0"),{x:12.5,y:7.05,w:0.7,h:0.3,fontFace:BF,fontSize:9,color:FAINT,align:"right"}); }
function src(s,t){ s.addText("Source: "+t,{x:0.6,y:7.02,w:11.6,h:0.3,fontFace:BF,fontSize:8.5,italic:true,color:FAINT}); }
function head(s,num,title,sub){
  s.addText(num,{x:0.6,y:0.5,w:0.62,h:0.62,fontFace:HF,fontSize:20,bold:true,color:WHITE,align:"center",valign:"middle",fill:{color:MINT},rectRadius:0.08,shape:p.ShapeType.roundRect});
  s.addText(title,{x:1.4,y:0.46,w:11.4,h:0.5,fontFace:HF,fontSize:25,bold:true,color:NAVY,valign:"middle",margin:0});
  if(sub) s.addText(sub,{x:1.42,y:0.98,w:11.3,h:0.32,fontFace:BF,fontSize:12.5,color:MUTED,italic:true,margin:0});
}
function statCard(s,x,y,w,big,label,col){
  s.addText(big,{x,y,w,h:0.72,fontFace:HF,fontSize:32,bold:true,color:col||NAVY,align:"center",valign:"middle",margin:0});
  s.addText(label,{x,y:y+0.72,w,h:0.5,fontFace:BF,fontSize:11.5,color:MUTED,align:"center",valign:"top",margin:0});
}
let s;

// 1 TITLE
s=p.addSlide(); s.background={color:INK};
s.addText("INVESTMENT COMMITTEE  ·  FEASIBILITY REVIEW",{x:0.9,y:1.45,w:11,h:0.4,fontFace:BF,fontSize:13,color:MINT,charSpacing:3,bold:true});
s.addText("Biotech Clinical-Catalyst Strategy",{x:0.85,y:1.95,w:11.8,h:1.4,fontFace:HF,fontSize:46,bold:true,color:WHITE,margin:0});
s.addText("Go long the clinical winners the crowd is busy shorting - and rent them the shares. Market-neutral.",{x:0.9,y:3.35,w:11.4,h:0.6,fontFace:BF,fontSize:18,color:ICE,margin:0});
s.addText([{text:"This study ASSUMES a predictive model (\"Alpha Forge\") and sizes the prize. ",options:{color:WHITE,bold:true}},{text:"Building that model is the next step.",options:{color:FAINT}}],{x:0.9,y:4.05,w:11.4,h:0.4,fontFace:BF,fontSize:14,margin:0});
[["$10M","assumed capital"],["2016-2019","320 catalysts"],["Long + lend","the strategy"],["~$100M","capacity"]].forEach((c,i)=>{const x=0.9+i*3.0;
  s.addText(c[0],{x,y:5.55,w:2.8,h:0.5,fontFace:HF,fontSize:22,bold:true,color:MINT,margin:0});
  s.addText(c[1],{x,y:6.05,w:2.8,h:0.35,fontFace:BF,fontSize:12,color:ICE,margin:0});});
s.addNotes("Quick intro. This is a feasibility study for a biotech trading strategy - we're NOT presenting a finished fund. One important naming thing: the STRATEGY is what I'll walk through today; 'Alpha Forge' is the name of the predictive MODEL we'd build to drive it - and we haven't built that yet. This whole study assumes such a model exists and asks 'if it did, is this worth doing?' The idea in one line: about 90% of biotech trials fail, so everyone shorts these stocks - we do the opposite, go long the ones we think win, and rent our shares to the shorts for a fee. I'll cover what a hedge fund is, our assumptions, the strategy, results, and where it breaks.");

// 2 MOTIVATION
s=p.addSlide(); s.background={color:WHITE};
head(s,"1","Motivation - why biotech, why now","Everyone shorts biotech into a catalyst. We take the educated opposite side.");
[["~90% of trials never reach approval","So shorting a biotech into its trial readout is the consensus, crowded trade."],
 ["Crowded shorts = rich borrow fees","When everyone shorts a name, the fee to borrow its shares to short goes sky-high."],
 ["We flip it","Go LONG the ones our model says will succeed - and LEND our shares to the crowd shorting them."],
 ["Two ways to win on one position","The stock re-rates up, AND we collect the borrow fee the whole time we hold."]].forEach((c,i)=>{const y=1.7+i*1.12;
  s.addText(String(i+1),{x:0.7,y,w:0.65,h:0.65,fontFace:HF,fontSize:20,bold:true,color:WHITE,align:"center",valign:"middle",fill:{color:MINT},rectRadius:0.32,shape:p.ShapeType.roundRect});
  s.addText(c[0],{x:1.55,y:y-0.02,w:4.7,h:0.7,fontFace:HF,fontSize:17,bold:true,color:NAVY,valign:"middle",margin:0});
  s.addText(c[1],{x:6.45,y:y-0.02,w:6.3,h:0.75,fontFace:BF,fontSize:13.5,color:INKT,valign:"middle",margin:0});});
src(s,"Clinical-trial success ~10% overall (Phase 1 -> approval): Wong, Siah & Lo, Biostatistics 2019; BIO/Informa 'Clinical Development Success Rates' 2021.");
pageno(s,2);
s.addNotes("The main point: we bet against the crowd on purpose. The chain is simple. Most biotech trials fail - roughly 9 in 10 drugs entering trials never get approved, and that's a well-documented number, it's on the slide. So the default trade is to short these stocks into a readout. When everyone's short, the cost to borrow the shares spikes. That's our opening: if our model can find the winners in that pile, we go long them, and because they're so heavily shorted we rent our shares to those short-sellers and collect the fee. So each position pays us twice - the stock goes up, and we earn rent while we hold. That rent is the piece most people overlook.");

// 3 WHAT IS A HEDGE FUND
s=p.addSlide(); s.background={color:WHITE};
head(s,"2","What is a hedge fund? (the 30-second version)","A pooled fund that tries to make money in any market - by 'hedging' out the parts it can't predict.");
s.addText([{text:"It pools investors' money and runs an active strategy. \"Hedging\" means ",options:{color:INKT}},
 {text:"cancelling out a risk you don't want",options:{bold:true,color:NAVY}},
 {text:" - here, we short the biotech ETF to remove \"did the whole sector go up or down,\" so we're left with just our stock-picking.",options:{color:INKT}}],
 {x:0.6,y:1.65,w:12.1,h:0.95,fontFace:BF,fontSize:15,lineSpacingMultiple:1.2,valign:"top"});
[["Average hedge fund","~8% / yr","the typical fund; many barely beat a plain index after fees"],
 ["Top-tier funds","~20-40% / yr","the best quant shops - rare, and hard to sustain"],
 ["What makes one 'good'","return per unit of risk","steady, uncorrelated to the market, survives bad years"]].forEach((c,i)=>{const x=0.6+i*4.05;
  s.addShape(p.ShapeType.roundRect,{x,y:2.95,w:3.75,h:2.45,fill:{color:"F4F6FC"},line:{color:LINE,width:1},rectRadius:0.09});
  s.addText(c[0],{x:x+0.3,y:3.15,w:3.15,h:0.7,fontFace:HF,fontSize:16,bold:true,color:NAVY,valign:"top",margin:0});
  s.addText(c[1],{x:x+0.3,y:3.8,w:3.15,h:0.6,fontFace:HF,fontSize:22,bold:true,color:MINT,margin:0});
  s.addText(c[2],{x:x+0.3,y:4.5,w:3.15,h:0.85,fontFace:BF,fontSize:12.5,color:INKT,valign:"top",margin:0});});
s.addText("Where this sits: a small, market-neutral, uncorrelated sleeve - not the next multi-billion flagship (see capacity slide).",
 {x:0.6,y:5.65,w:12.1,h:0.5,fontFace:BF,fontSize:13,color:MUTED,italic:true});
src(s,"Return ranges are industry estimates (HFR composite ~mid-single digits; top funds per press) - illustrative, verify before external use.");
pageno(s,3);
s.addNotes("This slide is just so nobody's lost, since the audience may not be finance people. A hedge fund pools money and runs an active bet to beat the market. The word 'hedge' is the key - it means cancelling a risk you don't want. In our case, we short the biotech ETF so that whether the whole sector rises or falls doesn't matter - we're left with just our own stock-picking. That's 'market-neutral.' For context on the bar: the average hedge fund makes about 8% a year, honestly not amazing; the superstars do 20 to 40% but that's rare. And 'good' isn't just high return - it's high return for the risk, steady, survives bad years. Those return numbers are industry estimates, so treat them as illustrative.");

// 4 ASSUMPTIONS
s=p.addSlide(); s.background={color:WHITE};
head(s,"3","What we're assuming (and the dataset)","Plain-English assumptions - plus the one honesty adjustment that matters most.");
s.addImage({path:`${R}/events_per_year.png`,x:0.5,y:1.7,w:5.9,h:3.28});
s.addText("Why only small companies?",{x:6.7,y:1.7,w:6.0,h:0.3,fontFace:HF,fontSize:14,bold:true,color:NAVY,margin:0});
s.addText("A big drugmaker has 20 drugs, so one trial barely moves its stock. A small biotech IS its one drug - so the price reaction is huge and tradeable. We only trade small-caps.",
 {x:6.7,y:2.02,w:6.0,h:0.9,fontFace:BF,fontSize:12.5,color:INKT,valign:"top",margin:0});
s.addText("We assume:",{x:6.7,y:3.0,w:6.0,h:0.3,fontFace:HF,fontSize:14,bold:true,color:NAVY,margin:0});
s.addText([{text:"·  Start with $10M (a test size).\n",options:{}},
 {text:"·  Put ~$500k (5%) in each name -> about 30 held at once.\n",options:{}},
 {text:"·  Trading + borrow costs (borrow fee has no public data, so we test a wide range).\n",options:{}},
 {text:"·  A model of some accuracy - we don't have it yet, so we test 100% / 90% / 80%.",options:{}}],
 {x:6.7,y:3.32,w:6.0,h:1.2,fontFace:BF,fontSize:12.5,color:INKT,lineSpacingMultiple:1.15,valign:"top",margin:0});
s.addShape(p.ShapeType.roundRect,{x:6.7,y:4.75,w:6.0,h:1.75,fill:{color:"FBF7EE"},line:{color:GOLD,width:1.2},rectRadius:0.09});
s.addText("The honesty adjustment (important)",{x:6.9,y:4.85,w:5.6,h:0.3,fontFace:HF,fontSize:13.5,bold:true,color:"9A6A12",margin:0});
s.addText([{text:"Our data is 68% winners - flattering (datasets over-capture notable, positive events). The real success rates for the readouts we trade are ~32% / 58% / 87% for Phase 2 / 3 / FDA. Blended by our mix = ",options:{color:INKT}},
 {text:"~56%. We re-run everything at 56% too.",options:{bold:true,color:"9A6A12"}}],
 {x:6.9,y:5.2,w:5.65,h:1.25,fontFace:BF,fontSize:12,lineSpacingMultiple:1.12,valign:"top",margin:0});
src(s,"Phase success rates: Wong, Siah & Lo 2019; BIO/Informa 2021 (Phase 2 ~28-35%, Phase 3 ~55-60%, regulatory ~85-90%).");
pageno(s,4);
s.addNotes("Let me lay out our assumptions plainly, because this matters. First, why only small companies - top right - a big drugmaker has twenty drugs, so one trial barely moves it, but a small biotech IS its one drug, so the stock reaction is huge and worth trading. That's a deliberate choice. Then the assumptions: we start with $10M as a test size; we put about $500k, which is 5%, into each name, so we hold roughly 30 at a time; we assume trading and borrow costs, and since there's no public data on borrow fees we test a wide range; and critically we assume a model of some accuracy - we don't have it, so we test perfect, 90%, and 80%. Now the gold box, the most important honesty point: our data is 68% winners, which is too high - datasets tend to over-capture the notable positive events. The real success rate for the Phase 2, 3 and FDA readouts we trade is about 56% blended. So we re-run every number at 56% as well - I'll always show both.");

// 5 FINDING
s=p.addSlide(); s.background={color:WHITE};
head(s,"4","The finding - where the money actually is","Approvals are mostly priced in early; the big move is on failure. We go long + hedge.");
s.addImage({path:`${R}/caar_path.png`,x:0.5,y:1.75,w:6.9,h:3.42});
let fy=1.85; [["Approvals are mostly priced in","winners drift up only ~+4% over our hold (median) - the market front-runs the good news"],
 ["Failures crash hard","a small-cap that misses drops ~-14% to -17% in a day - that's the real, sharp move"],
 ["Only in small-caps","a big-pharma readout barely moves the stock; a small-cap's whole value is one drug"],
 ["Success != stock up","even a real winner can drift down over 3 months - which is why we hedge and lend"]].forEach(c=>{ s.addText(c[0],{x:7.7,y:fy,w:5.1,h:0.4,fontFace:HF,fontSize:14.5,bold:true,color:NAVY,margin:0});
  s.addText(c[1],{x:7.7,y:fy+0.4,w:5.1,h:0.62,fontFace:BF,fontSize:12,color:INKT,valign:"top",margin:0}); fy+=1.02; });
pageno(s,5);
s.addNotes("The core insight, and it's a little counter-intuitive. Look at the price path. By the time an approval is announced, the stock has usually already drifted up - winners only rise about 4% over our whole hold, because the market front-runs the good news. The BIG, sharp moves happen on failure: a small-cap that misses its trial drops 14 to 17% in a single day. So the information is really in the surprise, and it's concentrated in small-caps - a big pharma company has twenty drugs so one readout is noise, but a small biotech is that one drug. Last point, and it's why we don't just bet on price: even a real winner can drift DOWN over three months. So we hedge out the market and we lend the shares for steady income, rather than relying on the stock always going up.");

// 6 STRATEGY
s=p.addSlide(); s.background={color:WHITE};
head(s,"5","The strategy - what we run, and what we cut","We'll cover the deployed strategy (long + lend) first, then why we tested and dropped shorting.");
[["Long + lend",MINT,"DEPLOYED - the engine","Buy the predicted winners ~1 month out, hold ~3 months, and rent the shares to the crowd shorting them. This is where the money is."],
 ["Short the failures",RED,"TESTED & DROPPED","We tried shorting the losers too. But the biggest-drop names are impossible to borrow, so after honest limits it loses money except in the best regime - cut."],
 ["Hedge with XBI",NAVY,"OPTIONAL - insurance","Short the biotech ETF to cancel out sector-wide moves (hedge against a broad biotech selloff). Costs a little; it's crash insurance, not profit."]].forEach((c,i)=>{const x=0.6+i*4.05;
  s.addShape(p.ShapeType.roundRect,{x,y:1.8,w:3.75,h:4.0,fill:{color:"F7F8FC"},line:{color:LINE,width:1},rectRadius:0.09});
  s.addShape(p.ShapeType.roundRect,{x:x+0.35,y:2.15,w:0.55,h:0.55,fill:{color:c[1]},line:{color:c[1]},rectRadius:0.28});
  s.addText(String(i+1),{x:x+0.35,y:2.15,w:0.55,h:0.55,fontFace:HF,fontSize:20,bold:true,color:WHITE,align:"center",valign:"middle",margin:0});
  s.addText(c[0],{x:x+1.05,y:2.17,w:2.5,h:0.55,fontFace:HF,fontSize:17,bold:true,color:NAVY,valign:"middle",margin:0});
  s.addText(c[2],{x:x+0.35,y:2.9,w:3.1,h:0.35,fontFace:BF,fontSize:11,bold:true,color:c[1],charSpacing:1,margin:0});
  s.addText(c[3],{x:x+0.35,y:3.35,w:3.1,h:2.3,fontFace:BF,fontSize:13,color:INKT,lineSpacingMultiple:1.2,valign:"top",margin:0});});
s.addText([{text:"Money comes from the stock re-rating + the lending fee. ",options:{bold:true,color:NAVY}},
 {text:"Short and hedge are risk controls, not return drivers.",options:{color:MUTED}}],
 {x:0.6,y:5.95,w:12.1,h:0.5,fontFace:BF,fontSize:14,valign:"top"});
pageno(s,6);
s.addNotes("Here's the roadmap for this slide: I'll explain the strategy we actually run - box one - then show you the short leg we tested and dropped, so you know why it's not there. So, box one, long and lend: buy the winners about a month before the catalyst, hold three months, and rent the shares out. That's the engine. Box two, being honest - we DID test shorting the losers, which sounds obvious since most fail. The problem: the juiciest shorts, the ones that crash hardest, are impossible to borrow, so once you're realistic that leg loses money except in the best case. We cut it. Box three, the hedge - we short the biotech ETF to cancel out sector-wide swings, so we're hedged against a broad biotech selloff. It costs a bit of return, so treat it as crash insurance, not a profit source. Bottom line: profit is long + lend; the other two just keep us safe.");

// 7 MECHANICS
s=p.addSlide(); s.background={color:WHITE};
head(s,"6","How the lending money is made","A daily rent that's richest before the catalyst, then fades.");
let ry=1.75; [["Position sizing","5% of capital per name, max 10% per company -> ~30 names at once."],
 ["Timing","enter ~1 month before the readout, exit ~3 months after."],
 ["Why hold through","you must hold the shares to rent them - the fee is richest while shorts pile in pre-catalyst."]].forEach(c=>{ s.addText(c[0],{x:0.6,y:ry,w:6.1,h:0.32,fontFace:HF,fontSize:14.5,bold:true,color:NAVY,margin:0});
  s.addText(c[1],{x:0.6,y:ry+0.34,w:6.1,h:0.7,fontFace:BF,fontSize:13,color:INKT,margin:0}); ry+=1.15; });
s.addShape(p.ShapeType.roundRect,{x:7.1,y:1.75,w:5.6,h:4.5,fill:{color:INK},line:{color:INK},rectRadius:0.09});
s.addText("Lending income (per position)",{x:7.4,y:1.95,w:5,h:0.4,fontFace:HF,fontSize:16,bold:true,color:MINT,margin:0});
s.addText("position x borrow rate x utilization x time",{x:7.4,y:2.45,w:5,h:0.5,fontFace:"Courier New",fontSize:12,color:ICE,margin:0});
s.addText("Utilization = the share of your holding actually out on loan (the rest earns nothing).",{x:7.4,y:3.0,w:5,h:0.7,fontFace:BF,fontSize:12,color:ICE,margin:0});
s.addShape(p.ShapeType.line,{x:7.4,y:3.85,w:5,h:0,line:{color:"34406B",width:1}});
s.addText("Example - $1M position, 100%/yr rate, 40% on loan",{x:7.4,y:3.95,w:5,h:0.35,fontFace:BF,fontSize:11.5,bold:true,color:ICE,margin:0});
s.addText([{text:"before the event (full rate) = $31,700\n",options:{}},{text:"after (rate fades)          = $10,000",options:{}}],
 {x:7.4,y:4.35,w:5,h:0.8,fontFace:"Courier New",fontSize:11,color:WHITE,lineSpacingMultiple:1.2,margin:0});
s.addText([{text:"total lending = $41,700 ",options:{color:MINT,bold:true}},{text:"(4.2% of the position, on top of the stock move)",options:{color:ICE}}],
 {x:7.4,y:5.35,w:5,h:0.6,fontFace:HF,fontSize:14,margin:0});
pageno(s,7);
s.addNotes("Quick on the mechanics so the lending number feels real. We put 5% in each name, hold about 30, enter a month before, exit three months after. Why hold the whole time even if it wobbles? Two reasons - you literally have to hold the shares to rent them out, and the rent is richest right before the catalyst when the shorts pile in. The formula is just your position times the borrow rate times 'utilization' - the fraction of your shares actually on loan - times time. In the example, a $1M position earns about $31k before the event and $10k after, so roughly $42k, about 4.2% - and that's ON TOP of whatever the stock does. Don't sweat the formula; the point is lending adds a few percent of steady income to every trade.");

// 8 RESULTS
s=p.addSlide(); s.background={color:WHITE};
head(s,"7","Results - over the 4 years, 2016-2019","Raw backtest vs the honest 56%-adjusted number we'd plan around.");
statCard(s,0.6,1.5,3.0,"$26.3M","backtest (68% data)",MINT);
statCard(s,3.65,1.5,3.0,"$22.3M","adjusted (56% real)",NAVY);
statCard(s,6.7,1.5,3.0,"~1.5","Sharpe (risk-adj.)",NAVY);
statCard(s,9.75,1.5,3.0,"-18%","worst dip (max DD)",RED);
s.addImage({path:`${R}/backtest_equity.png`,x:0.5,y:2.95,w:7.4,h:3.33});
const bh=(t)=>({text:t,options:{fontFace:BF,fontSize:11.5,bold:true,color:WHITE,fill:NAVY,valign:"middle",align:"center"}});
const bd=(t,o={})=>({text:t,options:{fontFace:BF,fontSize:11.5,color:INKT,valign:"middle",align:o.align||"center",...o}});
s.addTable([[{...bh("vs market (56% adj)"),options:{...bh("").options,align:"left"}},bh("$10M->"),bh("per yr")],
 [bd("Strategy (hedged)",{align:"left",bold:true,color:NAVY}),bd("$23M",{bold:true,color:MINT}),bd("22%",{bold:true})],
 [bd("Strategy (un-hedged)",{align:"left"}),bd("$27M"),bd("28%")],
 [bd("S&P 500 buy & hold",{align:"left"}),bd("$17M"),bd("13%")],
 [bd("XBI biotech buy & hold",{align:"left"}),bd("$14M"),bd("10%")]],
 {x:8.15,y:3.05,w:4.6,colW:[2.4,1.1,1.1],rowH:0.48,border:{type:"solid",color:LINE,pt:1},valign:"middle"});
s.addText([{text:"Sharpe ~1.5 = solid ",options:{bold:true,color:NAVY}},{text:"(above 1 is good) return for the risk taken. Max dip -18% = the worst peak-to-trough along the way. Never a losing 4-year run in the sims.",options:{color:MUTED}}],
 {x:8.15,y:5.5,w:4.6,h:1.0,fontFace:BF,fontSize:11.5,lineSpacingMultiple:1.15,valign:"top"});
pageno(s,8);
s.addNotes("Here's the headline, and note this is over the full four years, 2016 to 2019. The raw backtest turns $10M into $26.3M. But remember our honesty fix - adjust to the realistic 56% success rate and it's $22.3M. I'd lead with both: 'the backtest says 26, the number we'd actually plan around is 22.' Two risk numbers worth explaining in plain English: Sharpe of about 1.5 - that's return per unit of risk, and anything above 1 is considered good, so this is solid. And max drawdown of minus 18% - that's the worst dip from a peak along the way, so at some point you'd have been down 18% before recovering. The chart shows the adjusted strategy against the market: we end around $23M hedged, $27M un-hedged, versus the S&P at $17M and biotech at $14M. So even after haircutting ourselves, we beat the market - and we never have a losing four-year run in the simulations.");

// 9 WHERE PROFIT COMES FROM
s=p.addSlide(); s.background={color:WHITE};
head(s,"8","Is the profit the stock, or the lending? Every trade","Answer: ~77% from the stock going up, ~23% from lending fees - and we don't win them all.");
s.addImage({path:`${R}/per_trade_breakdown.png`,x:0.5,y:1.75,w:7.6,h:3.18});
const wh=(t)=>({text:t,options:{fontFace:BF,fontSize:12,bold:true,color:WHITE,fill:NAVY,valign:"middle",align:"center"}});
const wd=(t,o={})=>({text:t,options:{fontFace:BF,fontSize:12,color:INKT,valign:"middle",align:o.align||"center",...o}});
s.addTable([[{...wh("Trades ($M)"),options:{...wh("").options,align:"left"}},wh("Stock"),wh("Lend"),wh("Net")],
 [wd("118 winners",{align:"left",color:MINT,bold:true}),wd("+26.4"),wd("+2.5"),wd("+28.4",{bold:true})],
 [wd("90 losers",{align:"left",color:RED,bold:true}),wd("-11.9"),wd("+1.9"),wd("-10.4",{bold:true})],
 [wd("All 208 taken",{align:"left",bold:true,color:NAVY}),wd("+14.6"),wd("+4.3"),wd("+18.0",{bold:true,color:NAVY})]],
 {x:8.3,y:1.85,w:4.4,colW:[1.7,0.9,0.9,0.9],rowH:0.55,border:{type:"solid",color:LINE,pt:1},valign:"middle"});
s.addText([{text:"Stock ~77%, lending ~23%. ",options:{bold:true,color:NAVY}},
 {text:"90 of 208 trades still LOST on price (winners that drifted down) - lending pays on every one, cushioning them.",options:{color:INKT}}],
 {x:8.3,y:3.95,w:4.4,h:1.4,fontFace:BF,fontSize:12,lineSpacingMultiple:1.18,valign:"top"});
s.addText("208 traded of the 217 winners - ~9 were skipped when the book was already full (30-name cap).",
 {x:8.3,y:5.55,w:4.4,h:0.7,fontFace:BF,fontSize:11,italic:true,color:MUTED,valign:"top"});
pageno(s,9);
s.addNotes("The question this slide answers is: where does the profit actually come from - is it the stock picking, or the lending gimmick? Each bar is one real trade - blue is what the stock did, gold is the lending fee. Add it up: about 77% of the profit is the stock going up, 23% is lending. So it's mostly stock-picking, but lending is a real, meaningful chunk. Now the honest part in the table: 118 trades won, but 90 LOST money on the stock - those are cases where the trial succeeded but the stock still drifted down. We don't win them all. And here's why lending matters beyond the 23%: it pays on every single trade no matter what the stock does, so it steadily cushions those 90 losers. One number reconciliation, since someone will ask - earlier I said 217 winners; here it's 208 because about 9 got skipped when we already had our 30 positions full. Same book, just the ones we could fit.");

// 10 DOES IT NEED A MODEL
s=p.addSlide(); s.background={color:WHITE};
head(s,"9","Does it even need a model?","Yes - the model roughly adds 40%, and (more importantly) it protects you.");
statCard(s,1.0,2.0,3.4,"$16.3M","NO model (long everything)",MUTED);
s.addText("->",{x:4.6,y:2.1,w:1.0,h:1.0,fontFace:HF,fontSize:36,bold:true,color:MINT,align:"center",valign:"middle"});
statCard(s,5.7,2.0,3.4,"$22.3M","WITH a 90% model",MINT);
statCard(s,9.5,2.0,3.4,"+40%","the model's value",NAVY);
s.addText([{text:"At the realistic 56% rate, winners still slightly outnumber losers (~1.3 to 1) and lending pays - so even buying EVERYTHING makes money in this backtest. ",options:{color:INKT}},
 {text:"But that floor is fragile:",options:{bold:true,color:RED}},
 {text:" it leans on this being a friendly 2016-2019 market. The model's job is to lift the return AND keep it standing when winners get rarer (next slide).",options:{color:INKT}}],
 {x:1.0,y:3.75,w:11.3,h:1.4,fontFace:BF,fontSize:14.5,lineSpacingMultiple:1.22,valign:"top"});
s.addShape(p.ShapeType.roundRect,{x:1.0,y:5.4,w:11.3,h:1.05,fill:{color:"F0FAF6"},line:{color:MINT,width:1},rectRadius:0.08});
s.addText([{text:"Floor $16.3M (no skill)  ·  Realistic $22.3M (90% model)  ·  Ceiling $24.9M (perfect model). ",options:{bold:true,color:NAVY}},
 {text:"The model is what turns 'positive in a good market' into 'robust.'",options:{color:INKT}}],
 {x:1.25,y:5.52,w:10.8,h:0.8,fontFace:BF,fontSize:13.5,valign:"middle"});
pageno(s,10);
s.addNotes("Fair challenge: do you even need a fancy model, or are you just riding a good biotech market? So we tested the dumbest version - no model, just buy EVERY catalyst and lend. Even that makes $16M at the realistic 56% rate, because winners still slightly outnumber losers - about 1.3 to 1, not a huge edge - and lending pays on all of them. Add a decent 90% model and you get $22M, so the model is worth about 40% more. BUT - and this is important, someone will push on it - that no-model floor is fragile. It only works because 2016 to 2019 was a friendly period; in a worse market or with more failures, buying everything would lose. So I would NOT promise 'you can't lose by buying everything' - that's not true in general. The real value of the model is two things: it lifts the return, and it keeps the whole thing standing when winners get rare - which is exactly the next slide.");

// 11 MONTE CARLO
s=p.addSlide(); s.background={color:WHITE};
head(s,"10","Monte Carlo - do our assumption-guesses break it?","Hold model accuracy fixed; roll the uncertain cost assumptions 500 times (56% universe).");
// setup: held fixed vs drawn at random
s.addShape(p.ShapeType.roundRect,{x:0.6,y:1.6,w:5.95,h:1.55,fill:{color:"F4F6FC"},line:{color:LINE,width:1},rectRadius:0.08});
s.addText("HELD FIXED (the baseline)",{x:0.8,y:1.7,w:5.5,h:0.3,fontFace:BF,fontSize:11,bold:true,color:MUTED,charSpacing:1,margin:0});
s.addText("Model accuracy 90% (then 80%)\nPosition size 5%, ~30 names, timing\n(our design choices)",
 {x:0.8,y:2.05,w:5.5,h:1.0,fontFace:BF,fontSize:12.5,color:INKT,lineSpacingMultiple:1.15,valign:"top",margin:0});
s.addShape(p.ShapeType.roundRect,{x:6.75,y:1.6,w:5.95,h:1.55,fill:{color:"F0FAF6"},line:{color:MINT,width:1},rectRadius:0.08});
s.addText("DRAWN AT RANDOM each run",{x:6.95,y:1.7,w:5.5,h:0.3,fontFace:BF,fontSize:11,bold:true,color:"0A8F6E",charSpacing:1,margin:0});
s.addText("Borrow rate 25-250%/yr · Utilization 20-60%\nPost-event fade 5-25% · Trading cost 40-150 bps\n(the 4 market unknowns)",
 {x:6.95,y:2.05,w:5.5,h:1.0,fontFace:BF,fontSize:12.5,color:INKT,lineSpacingMultiple:1.15,valign:"top",margin:0});
// results table 90/80 x independent/correlated + precision
const mh=(t)=>({text:t,options:{fontFace:BF,fontSize:12,bold:true,color:WHITE,fill:NAVY,align:"center",valign:"middle"}});
const md=(t,o={})=>({text:t,options:{fontFace:BF,fontSize:12,color:INKT,align:o.align||"center",valign:"middle",...o}});
s.addTable([[{...mh("What varies (accuracy fixed)"),options:{...mh("").options,align:"left"}},mh("90% model - precision 92%"),mh("80% model - precision 84%")],
 [md("Assumptions drawn independently",{align:"left"}),md("$21.9M  [18.0, 27.8]"),md("$19.8M  [15.7, 25.6]")],
 [md("Assumptions correlated (all hit at once)",{align:"left",bold:true,color:NAVY}),md("$21.7M  [18.4, 26.6]",{bold:true}),md("$19.5M  [15.4, 24.3]",{bold:true})],
 [md("Chance of losing money (in the sims)",{align:"left",italic:true}),md("0%",{bold:true,color:MINT}),md("0%",{bold:true,color:MINT})]],
 {x:0.6,y:3.35,w:12.1,colW:[4.9,3.6,3.6],rowH:0.55,border:{type:"solid",color:LINE,pt:1},valign:"middle"});
s.addText([{text:"Read: ",options:{bold:true,color:NAVY}},
 {text:"a typical run makes ~$22M; even the unlucky 5% stays ~$18M, above the $10M start. Correlating the assumptions (a stress regime hits all at once) barely trims it. So the cost guesses don't break it. ",options:{color:INKT}},
 {text:"Caveat: every run uses 2016-2019 prices, so \"0% loss\" means in a market like that one.",options:{bold:true,color:"9A6A12"}}],
 {x:0.6,y:5.75,w:12.1,h:0.85,fontFace:BF,fontSize:13,lineSpacingMultiple:1.15,valign:"top"});
s.addText("Precision (in the header) = when the model says \"success,\" how often it's right; 92% here because we're at the realistic 56% base rate (next slide).",
 {x:0.6,y:6.68,w:12.1,h:0.35,fontFace:BF,fontSize:11,italic:true,color:MUTED});
pageno(s,11);
s.addNotes("This is the uncertainty slide, and it follows a specific structure. First, the setup up top: we HOLD the model accuracy fixed - at 90%, then 80% - and we hold our own design choices fixed, like sizing and timing. What we DRAW AT RANDOM are the four things we genuinely don't know: the borrow rate, utilization, the post-event fade, and trading cost - each over a wide range. Then we re-ran the strategy 500 times. The table: at a 90% model the typical run makes about $22M, with 90% of runs between $18M and $27M; at 80% it's about $19.5M. We draw the assumptions two ways - independently, and correlated, meaning a bad-liquidity regime hits all of them at once - and even correlated it barely moves. Crucially, zero runs lose money. Note the header says 'precision 92%' - that's how often the model's 'success' call is actually right, and it's high because we're at the realistic 56% base rate, which is the next slide. The honest caveat: this only shuffles the cost guesses; every run still uses 2016-2019 prices, so '0% loss' means in a market like that one.");

// 12 PRECISION
s=p.addSlide(); s.background={color:WHITE};
head(s,"11","Why we adjusted to 56% - it's all about precision","Remember the 56% honesty cut? Here's why it matters so much: a '90% accurate' model can still be wrong half the time.");
s.addText("Imagine 1,000 companies where only 10% succeed. Even a 90%-accurate model:",{x:0.6,y:1.7,w:12,h:0.4,fontFace:BF,fontSize:14,bold:true,color:NAVY});
const ph=(t)=>({text:t,options:{fontFace:BF,fontSize:13,bold:true,color:WHITE,fill:NAVY,align:"center",valign:"middle"}});
const pd2=(t,o={})=>({text:t,options:{fontFace:BF,fontSize:13,color:INKT,align:"center",valign:"middle",...o}});
s.addTable([[{...ph(""),options:{...ph("").options}},ph("Model says SUCCESS"),ph("Model says fail")],
 [pd2("100 real winners",{bold:true,align:"left"}),pd2("90 caught",{color:MINT}),pd2("10 missed")],
 [pd2("900 real failures",{bold:true,align:"left"}),pd2("90 LANDMINES",{color:RED,bold:true}),pd2("810 avoided")]],
 {x:0.6,y:2.2,w:7.5,colW:[2.7,2.6,2.2],rowH:0.6,border:{type:"solid",color:LINE,pt:1},valign:"middle"});
s.addShape(p.ShapeType.roundRect,{x:8.35,y:2.2,w:4.35,h:1.8,fill:{color:"FBF3F2"},line:{color:RED,width:1.2},rectRadius:0.09});
s.addText("We'd buy 180, only 90 are real",{x:8.55,y:2.35,w:4,h:0.4,fontFace:HF,fontSize:15,bold:true,color:RED,margin:0});
s.addText("= precision 50%. Half the book is landmines that crash - even though the model is '90% accurate.'",
 {x:8.55,y:2.78,w:4,h:1.1,fontFace:BF,fontSize:13,color:INKT,valign:"top",margin:0});
s.addText([{text:"So why is 56% the whole game? ",options:{bold:true,color:NAVY}},
 {text:"The rarer the winners, the more failures sneak in as \"landmines.\" At a 10% success rate a 90% model is only 50% precise. At OUR realistic 56%, that same model is 92% precise - it holds up. That's exactly why we insisted on 56% instead of a made-up rosy number.",options:{color:INKT}}],
 {x:0.6,y:4.4,w:12.1,h:1.3,fontFace:BF,fontSize:14,lineSpacingMultiple:1.2,valign:"top"});
s.addText("Precision = when the model says \"success,\" how often it's actually right. A wrong pick gets bought and crashes ~15%.",
 {x:0.6,y:5.85,w:12.1,h:0.5,fontFace:BF,fontSize:12,color:MUTED,italic:true});
pageno(s,12);
s.addNotes("This ties directly back to that 56% adjustment - here's WHY it mattered so much. The trap is that 'accuracy' can fool you. Picture 1,000 companies where only 10% win. Even a 90%-accurate model catches 90 of the 100 winners, but it also wrongly flags 90 of the 900 losers as winners. So it says 'success' to 180 names and only half are actually real - that's 'precision' of 50%. Half your book would be landmines that crash, even though the model is technically 90% accurate. That's the base-rate trap. Now connect it: the rarer winners are, the worse precision gets. That's the entire reason we refused to just use our flattering 68% and instead adjusted to the realistic 56% - because at 56% that same 90% model is 92% precise and holds up, whereas in a 10% world it would fall apart. Message to whoever builds the model: chase precision, not just accuracy.");

// 13 WHAT COULD BREAK IT
s=p.addSlide(); s.background={color:WHITE};
head(s,"12","What could break it","The honest list - what we assumed, and what we can't yet know.");
const ch=(t)=>({text:t,options:{fontFace:BF,fontSize:12.5,bold:true,color:WHITE,fill:NAVY,align:"center",valign:"middle"}});
const cd=(t,o={})=>({text:t,options:{fontFace:BF,fontSize:12.5,color:INKT,align:o.align||"left",valign:"middle",...o}});
const conf=(t,c)=>({text:t,options:{fontFace:BF,fontSize:12,bold:true,color:c,align:"center",valign:"middle"}});
s.addTable([[{...ch("Assumption"),options:{...ch("").options,align:"left"}},ch("What we used"),ch("Confidence")],
 [cd("Model precision"),cd("90% acc -> 92% precision at 56%",{align:"center"}),conf("the big unknown",RED)],
 [cd("Borrow rate / utilization"),cd("100%/yr, 40% (assumed)",{align:"center"}),conf("no data - swept",RED)],
 [cd("Timing & costs"),cd("~1mo before / 3mo after, ~0.85%",{align:"center"}),conf("grounded",MINT)],
 [cd("Market regime"),cd("all sims use 2016-2019 prices",{align:"center"}),conf("not stress-tested",GOLD)],
 [cd("The hedge"),cd("on (optional)",{align:"center"}),conf("cost return here",GOLD)]],
 {x:0.6,y:1.75,w:12.1,colW:[4.2,5.0,2.9],rowH:0.55,border:{type:"solid",color:LINE,pt:1},valign:"middle"});
s.addShape(p.ShapeType.roundRect,{x:0.6,y:5.35,w:12.1,h:1.1,fill:{color:"FBF7EE"},line:{color:GOLD,width:1},rectRadius:0.08});
s.addText([{text:"Biggest caveat: ",options:{bold:true,color:"9A6A12"}},
 {text:"'never loses' is conditional on a 2016-2019-like market - every simulated path comes from that window. A broad sector crash is a separate risk, which is what the optional hedge is insurance against.",options:{color:INKT}}],
 {x:0.85,y:5.48,w:11.6,h:0.85,fontFace:BF,fontSize:13,valign:"middle"});
pageno(s,13);
s.addNotes("I'd rather flag our own weak spots than have someone find them. Top of the list, in red: model precision - we don't have the model yet, so the 92% is a target, not a fact, and everything hinges on it. Borrow economics we assumed with no hard data, though we stress-tested a wide range. Timing and trading costs are solid, grounded in the data. Two amber ones people miss: first, every simulation uses 2016-to-2019 prices, so when I say 'never loses,' that means never loses IN a market like that one - a real sector crash is a separate risk, and that's exactly what the optional hedge insures against. Second, the hedge itself actually cost us return in this friendly window. None of these are dealbreakers, but that's the honest fine print, and I wanted you to hear it from us.");

// 14 SCALABILITY
s=p.addSlide(); s.background={color:WHITE};
head(s,"13","How big can it get? ~$100M","Small-cap liquidity caps it - a boutique sleeve, not a mega-fund.");
let sy=1.75; [["You can safely trade ~10-20% of a stock's daily volume","push past that in a day and your own buying visibly moves the price against you"],
 ["Over our ~1-month entry window, that's roughly one full day's volume per position","the median name we trade only turns over ~$3.3M a day - so a position tops out around $3-5M"],
 ["A $3-5M position is our 5% slice","so the fund can be about 20x that - roughly $67M to $134M -> call it ~$100M"]].forEach((c,i)=>{ s.addText(String(i+1),{x:0.7,y:sy,w:0.6,h:0.6,fontFace:HF,fontSize:18,bold:true,color:WHITE,align:"center",valign:"middle",fill:{color:NAVY},rectRadius:0.3,shape:p.ShapeType.roundRect});
  s.addText(c[0],{x:1.5,y:sy-0.05,w:5.6,h:0.85,fontFace:HF,fontSize:14,bold:true,color:NAVY,valign:"middle",margin:0});
  s.addText(c[1],{x:7.3,y:sy-0.05,w:5.4,h:0.85,fontFace:BF,fontSize:12.5,color:INKT,valign:"middle",margin:0}); sy+=1.2; });
s.addShape(p.ShapeType.roundRect,{x:0.6,y:5.35,w:12.1,h:1.1,fill:{color:"F4F6FC"},line:{color:NAVY,width:1},rectRadius:0.08});
s.addText([{text:"Deployable ~$50-150M, call it ~$100M. ",options:{bold:true,color:NAVY}},
 {text:"Push past that and you either skip the thinnest names or pay far more to trade - the edge erodes. A high-return niche sleeve, not a flagship.",options:{color:INKT}}],
 {x:0.85,y:5.47,w:11.6,h:0.9,fontFace:BF,fontSize:13.5,valign:"middle"});
src(s,"Median daily $ volume from 2016-2019 trading data for 88 of the 91 names we traded.");
pageno(s,14);
s.addNotes("How much money can this hold? About $100M, and let me build it up properly rather than just asserting it. Start with the real constraint: to avoid moving the price, you can only safely trade about 10 to 20% of a stock's daily volume in a day - trade more and everyone sees a big buyer and the price runs away from you. Now, we build a position gradually over our roughly one-month entry window, and adding it up that safely lets you accumulate about one full day's volume in total per name. The stocks we trade are tiny - the typical one only trades about $3.3M a day - so a position tops out around $3 to $5M. THAT position is our 5% slice of the fund, so the fund can be roughly 20 times that, which lands at $67 to $134M - call it $100M. Past that you're forced to skip the smallest names or pay up, and the edge bleeds away. So it's a sharp niche fund, not a giant - which is fine for an uncorrelated sleeve.");

// 15 RECOMMENDATION
s=p.addSlide(); s.background={color:INK};
s.addText("Recommendation",{x:0.85,y:0.7,w:11.6,h:0.8,fontFace:HF,fontSize:34,bold:true,color:WHITE,margin:0});
s.addText("The economics work. The whole bet now rides on one thing: can we build a precise enough model?",
 {x:0.87,y:1.55,w:11.6,h:0.5,fontFace:BF,fontSize:16,color:ICE,italic:true,margin:0});
let ry2=2.25; [["Proven",MINT,"Long+lend beats the market even after the honest 56% haircut ($22M, 22%/yr, never a losing 4-year run in the sims). Lending adds ~19%. There's a positive floor even with zero skill in a normal market."],
 ["The catch",GOLD,"It all hinges on model precision - at a realistic base rate a 90% model works, but precision (not raw accuracy) is what keeps landmines out of the book."],
 ["Next steps",WHITE,"1) Build & validate the model ('Alpha Forge') - measure its precision.  2) Add a stop-loss to cut drifters and misclassified landmines.  3) Confirm borrow economics with a prime broker.  Run it as a capacity-limited (~$100M) uncorrelated sleeve."]].forEach(c=>{ s.addShape(p.ShapeType.roundRect,{x:0.85,y:ry2,w:11.6,h:1.3,fill:{color:"232C4D"},line:{color:"34406B",width:1},rectRadius:0.09});
  s.addText(c[0].toUpperCase(),{x:1.1,y:ry2+0.15,w:2.4,h:0.9,fontFace:HF,fontSize:15,bold:true,color:c[1],valign:"top",margin:0});
  s.addText(c[2],{x:3.4,y:ry2+0.15,w:8.9,h:1.0,fontFace:BF,fontSize:12.5,color:ICE,lineSpacingMultiple:1.12,valign:"middle",margin:0}); ry2+=1.45; });
pageno(s,15);
s.addNotes("To wrap up - the ask. The economics work: even after we haircut ourselves to the realistic 56%, long+lend makes about $22M, 22% a year, never has a losing four-year run in the sims, and beats the market, with lending adding about a fifth of the profit. And there's a positive floor even with no skill in a normal market. The catch - the whole thing now hinges on one question: can we build a model that's not just accurate but PRECISE, so we keep the landmines out. So the next steps are concrete: build and validate the model - that's the 'Alpha Forge' piece - and measure its precision; add a stop-loss to cut the losers and any landmines; and confirm the borrow economics with a real prime broker. And we'd run it as roughly a $100M uncorrelated sleeve, not a flagship. Recommendation: proceed to build the model.");

p.writeFile({fileName:`${R}/Biotech_Catalyst_Strategy_Deck.pptx`}).then(f=>console.log("WROTE",f));
