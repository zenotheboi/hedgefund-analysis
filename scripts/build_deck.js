const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.defineLayout({ name: "W", width: 13.333, height: 7.5 }); p.layout = "W";
const R = "/Users/gigi/hedgefund-analysis/reports";
const NAVY="1E2761", INK="141B33", ICE="CADCFC", MINT="02C39A", RED="C0392F",
      MUTED="5B636E", LINE="E4E6EE", WHITE="FFFFFF", FAINT="8A919B", GOLD="E0A458";
const HF="Cambria", BF="Calibri", INKT="27313F";

function pageno(s,n){ s.addText(String(n).padStart(2,"0"),{x:12.5,y:7.02,w:0.7,h:0.3,fontFace:BF,fontSize:9,color:FAINT,align:"right"}); }
function head(s,num,title,sub){
  s.addText(num,{x:0.6,y:0.5,w:0.62,h:0.62,fontFace:HF,fontSize:20,bold:true,color:WHITE,align:"center",valign:"middle",fill:{color:MINT},rectRadius:0.08,shape:p.ShapeType.roundRect});
  s.addText(title,{x:1.4,y:0.46,w:11.4,h:0.5,fontFace:HF,fontSize:26,bold:true,color:NAVY,valign:"middle",margin:0});
  if(sub) s.addText(sub,{x:1.42,y:0.98,w:11.3,h:0.32,fontFace:BF,fontSize:12.5,color:MUTED,italic:true,margin:0});
}
function statCard(s,x,y,w,big,label,col){
  s.addText(big,{x,y,w,h:0.72,fontFace:HF,fontSize:32,bold:true,color:col||NAVY,align:"center",valign:"middle",margin:0});
  s.addText(label,{x,y:y+0.72,w,h:0.5,fontFace:BF,fontSize:11.5,color:MUTED,align:"center",valign:"top",margin:0});
}
let s;

// 1 TITLE
s=p.addSlide(); s.background={color:INK};
s.addText("INVESTMENT COMMITTEE  ·  FEASIBILITY REVIEW",{x:0.9,y:1.5,w:11,h:0.4,fontFace:BF,fontSize:13,color:MINT,charSpacing:3,bold:true});
s.addText("Alpha Forge",{x:0.85,y:2.0,w:11.6,h:1.2,fontFace:HF,fontSize:60,bold:true,color:WHITE,margin:0});
s.addText("A market-neutral biotech strategy: go long the clinical winners the crowd is busy shorting, and rent them the shares.",{x:0.9,y:3.35,w:11.2,h:0.7,fontFace:BF,fontSize:18,color:ICE,margin:0});
[["$10M","test capital"],["2016-2019","320 catalysts"],["Long + lend","the strategy"],["~$100M","capacity"]].forEach((c,i)=>{const x=0.9+i*3.0;
  s.addText(c[0],{x,y:5.5,w:2.8,h:0.5,fontFace:HF,fontSize:22,bold:true,color:MINT,margin:0});
  s.addText(c[1],{x,y:6.0,w:2.8,h:0.35,fontFace:BF,fontSize:12,color:ICE,margin:0});});
s.addText("Feasibility study - README Step 2 (assume a model, size the prize, then stress it hard).",{x:0.9,y:6.7,w:11,h:0.3,fontFace:BF,fontSize:12,color:FAINT,italic:true,margin:0});
s.addNotes("Quick intro: this is Alpha Forge, a feasibility study - we're NOT saying 'here's a finished fund.' The whole idea in one line: about 90% of biotech trials fail, so everyone piles in to short these stocks. Our strategy does the opposite - we go long the ones we think will succeed, and because the crowd is shorting them, we can rent our shares out and collect a fat fee on top. I'll walk through what a hedge fund is first, then our assumptions, the strategy, the results, and - most importantly - where it could break.");

// 2 MOTIVATION
s=p.addSlide(); s.background={color:WHITE};
head(s,"1","Motivation - why biotech, why now","Everyone shorts biotech into a catalyst. We take the educated opposite side.");
[["~90% of clinical trials fail","So shorting a biotech into its trial readout is the consensus, crowded trade."],
 ["Crowded shorts = rich borrow fees","When everyone shorts a name, the fee to borrow its shares goes sky-high."],
 ["We flip it","Go LONG the ones our model says will succeed - and LEND our shares to the crowd shorting them."],
 ["Two ways to win on one position","The stock re-rates up, AND we collect the borrow fee the whole time we hold."]].forEach((c,i)=>{const y=1.75+i*1.15;
  s.addText(String(i+1),{x:0.7,y,w:0.65,h:0.65,fontFace:HF,fontSize:20,bold:true,color:WHITE,align:"center",valign:"middle",fill:{color:MINT},rectRadius:0.32,shape:p.ShapeType.roundRect});
  s.addText(c[0],{x:1.55,y:y-0.02,w:4.6,h:0.7,fontFace:HF,fontSize:17,bold:true,color:NAVY,valign:"middle",margin:0});
  s.addText(c[1],{x:6.35,y:y-0.02,w:6.4,h:0.75,fontFace:BF,fontSize:13.5,color:INKT,valign:"middle",margin:0});});
pageno(s,2);
s.addNotes("The main point: we're betting against the crowd, on purpose. Here's the logic chain - most biotech trials fail, so the default trade is to short these stocks going into a readout. When everyone's short, the cost to borrow the shares spikes. That's the opening: if OUR model can pick the winners in that pile, we go long them, and because they're so heavily shorted, we rent our shares to those short-sellers and pocket the fee. So one position pays us twice - the stock goes up, and we collect rent along the way. That 'rent' is the piece most people miss, and it's a big part of our edge.");

// 3 WHAT IS A HEDGE FUND
s=p.addSlide(); s.background={color:WHITE};
head(s,"2","What is a hedge fund? (the 30-second version)","A pooled fund that tries to make money in any market - often market-neutral.");
s.addText([{text:"A hedge fund pools investors' money and runs an active strategy to beat the market - ",options:{color:INKT}},
 {text:"often aiming to make money whether the market goes up OR down (\"market-neutral\").",options:{bold:true,color:NAVY}}],
 {x:0.6,y:1.7,w:12.1,h:0.9,fontFace:BF,fontSize:16,lineSpacingMultiple:1.2,valign:"top"});
[["Average hedge fund","~8%/yr","the typical fund barely beats a simple index after fees"],
 ["Top-tier funds","~20-40%/yr","the best quant shops - rare, and hard to sustain"],
 ["What makes one 'good'","return per unit of risk","steady, uncorrelated to the market, survives bad years"]].forEach((c,i)=>{const x=0.6+i*4.05;
  s.addShape(p.ShapeType.roundRect,{x,y:2.9,w:3.75,h:2.5,fill:{color:"F4F6FC"},line:{color:LINE,width:1},rectRadius:0.09});
  s.addText(c[0],{x:x+0.3,y:3.1,w:3.15,h:0.7,fontFace:HF,fontSize:16,bold:true,color:NAVY,valign:"top",margin:0});
  s.addText(c[1],{x:x+0.3,y:3.75,w:3.15,h:0.6,fontFace:HF,fontSize:23,bold:true,color:MINT,margin:0});
  s.addText(c[2],{x:x+0.3,y:4.45,w:3.15,h:0.85,fontFace:BF,fontSize:12.5,color:INKT,valign:"top",margin:0});});
s.addText("Where Alpha Forge aims to sit: a small, market-neutral, uncorrelated sleeve - not the next multi-billion flagship (see capacity).",
 {x:0.6,y:5.7,w:12.1,h:0.5,fontFace:BF,fontSize:13,color:MUTED,italic:true});
pageno(s,3);
s.addNotes("This slide is just so nobody's lost - the audience may not live in finance. Simplest version: a hedge fund takes investors' money and runs an active bet to beat the market, and the good ones make money even when the market falls - that's 'market-neutral.' For context: the average hedge fund does about 8% a year - honestly not amazing. The superstar funds do 20 to 40%, but that's rare and hard to keep up. A 'good' strategy isn't just high return - it's high return for the risk taken, steady, and not just riding the market up. Keep that bar in mind when we get to our numbers. And flag: our figures are early-stage, not audited fund returns.");

// 4 ASSUMPTIONS & DATASET
s=p.addSlide(); s.background={color:WHITE};
head(s,"3","Assumptions & dataset","2016-2019 small-cap readouts - and the one honesty adjustment that matters most.");
s.addImage({path:`${R}/events_per_year.png`,x:0.5,y:1.7,w:6.4,h:3.56});
let ay=1.75; [["Capital / sizing","$10M start, 5% per name, ~30 open at once"],
 ["Costs","borrow fee (assumed, swept), 80+5 bps trading"],
 ["Model accuracy","no model yet - we test 100% / 90% / 80%"]].forEach(c=>{ s.addText(c[0],{x:7.2,y:ay,w:5.5,h:0.32,fontFace:HF,fontSize:14.5,bold:true,color:NAVY,margin:0});
  s.addText(c[1],{x:7.2,y:ay+0.34,w:5.5,h:0.5,fontFace:BF,fontSize:12.5,color:INKT,margin:0}); ay+=0.95; });
s.addShape(p.ShapeType.roundRect,{x:7.2,y:4.55,w:5.5,h:1.9,fill:{color:"FBF7EE"},line:{color:GOLD,width:1.2},rectRadius:0.09});
s.addText("Selection-bias adjustment (important)",{x:7.4,y:4.65,w:5.1,h:0.35,fontFace:HF,fontSize:14,bold:true,color:"9A6A12",margin:0});
s.addText([{text:"Our sample is 68% success - flattering. We trade Phase 2/3/FDA readouts, whose real rates are ~32% / 58% / 87%. Blended by our mix = ",options:{color:INKT}},
 {text:"~56% realistic.",options:{bold:true,color:"9A6A12"}},{text:" We re-run everything at 56% too.",options:{color:INKT}}],
 {x:7.4,y:5.05,w:5.15,h:1.3,fontFace:BF,fontSize:12.5,lineSpacingMultiple:1.15,valign:"top",margin:0});
pageno(s,4);
s.addNotes("Two things here. First the setup: 320 small-cap catalyst events, 2016 to 2019 - green bars are successes, red are failures, roughly 2 to 1. We start with $10M, 5% per name, hold about 30 at a time. Now the important bit - the gold box. Our dataset is 68% winners, which is suspiciously high. That's selection bias - the data over-represents winners. So we asked: what's the REAL success rate for the events we actually trade? We trade Phase 2, Phase 3 and FDA readouts - those succeed about 32%, 58% and 87% of the time. Blend that by our mix and you get about 56%. The honest thing - and this is what a smart reviewer would demand - is we re-run every result at 56% too, not just our flattering 68%. I'll show both.");

// 5 THE FINDING
s=p.addSlide(); s.background={color:WHITE};
head(s,"4","The finding - where the money actually is","Approvals are mostly priced in early; the move is on the surprise. We position long + hedge.");
s.addImage({path:`${R}/caar_path.png`,x:0.5,y:1.75,w:6.9,h:3.42});
let fy=1.9; [["Approvals are largely priced in","by the time the news hits, the stock has often already moved - the reaction is small"],
 ["The signal lives in small-caps","a big-pharma readout barely moves the stock; a small-cap's whole value is one drug"],
 ["Success != the stock goes up","even a real winner can drift down over our 3-month hold - which is why we hedge and lend"]].forEach(c=>{ s.addText(c[0],{x:7.7,y:fy,w:5.1,h:0.5,fontFace:HF,fontSize:15,bold:true,color:NAVY,margin:0});
  s.addText(c[1],{x:7.7,y:fy+0.48,w:5.1,h:0.8,fontFace:BF,fontSize:12.5,color:INKT,valign:"top",margin:0}); fy+=1.28; });
pageno(s,5);
s.addNotes("The core insight - and it's a bit counter-intuitive. Look at the price path: by the time an approval is announced, the stock has usually already moved. The market prices it in ahead of time, so the reaction on the day is small. The real sharp moves come on surprises. Two things follow. One, this only works in small-caps - a big pharma company has 20 drugs, so one readout barely moves it, but a small biotech IS that one drug. Two, and this is key: a trial succeeding does NOT guarantee the stock goes up over our window - plenty of winners still drift down. That's exactly why we don't just bet on price - we hedge out the market and we lend the shares for steady income. So I'd frame it as: we go long the winners but protect ourselves, rather than 'failure is the only thing that matters.'");

// 6 STRATEGY
s=p.addSlide(); s.background={color:WHITE};
head(s,"5","The strategy - deployed = long + lend","We tested a short leg and a hedge; only long+lend is the engine.");
[["Long + lend",MINT,"DEPLOYED - the engine","Buy the predicted winners ~1 month out, hold ~3 months, and rent the shares to the crowd shorting them."],
 ["Short the failures",RED,"TESTED & DROPPED","We tested shorting the losers. After honest borrow limits it loses money except in the best regime - so we cut it."],
 ["Hedge with XBI",NAVY,"OPTIONAL - insurance","Short the biotech ETF to strip out market direction. Costs a bit; it's crash insurance, not a profit source."]].forEach((c,i)=>{const x=0.6+i*4.05;
  s.addShape(p.ShapeType.roundRect,{x,y:1.8,w:3.75,h:3.9,fill:{color:"F7F8FC"},line:{color:LINE,width:1},rectRadius:0.09});
  s.addShape(p.ShapeType.roundRect,{x:x+0.35,y:2.15,w:0.55,h:0.55,fill:{color:c[1]},line:{color:c[1]},rectRadius:0.28});
  s.addText(String(i+1),{x:x+0.35,y:2.15,w:0.55,h:0.55,fontFace:HF,fontSize:20,bold:true,color:WHITE,align:"center",valign:"middle",margin:0});
  s.addText(c[0],{x:x+1.05,y:2.17,w:2.5,h:0.55,fontFace:HF,fontSize:18,bold:true,color:NAVY,valign:"middle",margin:0});
  s.addText(c[2],{x:x+0.35,y:2.9,w:3.1,h:0.35,fontFace:BF,fontSize:11,bold:true,color:c[1],charSpacing:1,margin:0});
  s.addText(c[3],{x:x+0.35,y:3.35,w:3.1,h:2.1,fontFace:BF,fontSize:13.5,color:INKT,lineSpacingMultiple:1.2,valign:"top",margin:0});});
s.addText([{text:"Money comes from the stock re-rating + the lending fee. ",options:{bold:true,color:NAVY}},
 {text:"The short leg and the hedge are risk controls, not return drivers.",options:{color:MUTED}}],
 {x:0.6,y:5.85,w:12.1,h:0.6,fontFace:BF,fontSize:14,valign:"top"});
pageno(s,6);
s.addNotes("So what do we actually run? Just the first box - long and lend. Buy the winners about a month before the catalyst, hold three months, rent the shares out. That's the engine. Now, being honest: we ALSO tested shorting the losers - sounds obvious, right, most fail. But once you account for the fact that the juiciest shorts are impossible to borrow, that leg loses money except in the best conditions, so we dropped it. And we tested a hedge - shorting the biotech ETF to cancel out market swings. It costs a little return, so think of it as crash insurance, not a money-maker. Bottom line: the profit is long + lend; the other two just keep us safe.");

// 7 MECHANICS
s=p.addSlide(); s.background={color:WHITE};
head(s,"6","How the lending money is made","A daily rent that's richest before the catalyst, then fades.");
let ry=1.75; [["Position sizing","5% of capital per name, max 10% per company, 150% gross -> ~30 names at once."],
 ["Timing","enter ~1 month before the readout (T-20), exit ~3 months after (T+63)."],
 ["Why hold through","you must hold the shares to rent them - the fee is richest while shorts pile in pre-catalyst."]].forEach(c=>{ s.addText(c[0],{x:0.6,y:ry,w:6.1,h:0.32,fontFace:HF,fontSize:14.5,bold:true,color:NAVY,margin:0});
  s.addText(c[1],{x:0.6,y:ry+0.34,w:6.1,h:0.7,fontFace:BF,fontSize:13,color:INKT,margin:0}); ry+=1.15; });
s.addShape(p.ShapeType.roundRect,{x:7.1,y:1.75,w:5.6,h:4.5,fill:{color:INK},line:{color:INK},rectRadius:0.09});
s.addText("Lending income (per position)",{x:7.4,y:1.95,w:5,h:0.4,fontFace:HF,fontSize:16,bold:true,color:MINT,margin:0});
s.addText("notional x rate x utilization x days/252",{x:7.4,y:2.45,w:5,h:0.5,fontFace:"Courier New",fontSize:12.5,color:ICE,margin:0});
s.addText("Utilization = the share of your position actually out on loan (the rest earns nothing).",{x:7.4,y:3.0,w:5,h:0.7,fontFace:BF,fontSize:12,color:ICE,margin:0});
s.addShape(p.ShapeType.line,{x:7.4,y:3.85,w:5,h:0,line:{color:"34406B",width:1}});
s.addText("Worked example - $1M position, 100%/yr, 40% utilization",{x:7.4,y:3.95,w:5,h:0.35,fontFace:BF,fontSize:11.5,bold:true,color:ICE,margin:0});
s.addText([{text:"pre-catalyst (20d, full rate)   = $31,700\n",options:{}},{text:"post-catalyst (63d, faded)      = $10,000",options:{}}],
 {x:7.4,y:4.35,w:5,h:0.8,fontFace:"Courier New",fontSize:11,color:WHITE,lineSpacingMultiple:1.2,margin:0});
s.addText([{text:"total lending = $41,700 ",options:{color:MINT,bold:true}},{text:"(4.2% of the position, on top of the stock move)",options:{color:ICE}}],
 {x:7.4,y:5.35,w:5,h:0.6,fontFace:HF,fontSize:14,margin:0});
pageno(s,7);
s.addNotes("Quick on the mechanics so the lending number feels real. We put 5% in each name, hold about 30, enter a month before, exit three months after. Why hold the whole time even if it wobbles? Two reasons - you literally have to hold the shares to rent them out, and the rent is richest right before the catalyst when the shorts are piling in. The formula's simple: your position times the borrow rate times 'utilization' - that's just the fraction of your shares actually on loan - times the time. Worked example: a $1M position earns about $31k before the event and $10k after, so about $42k, roughly 4.2% - and that's ON TOP of whatever the stock does. Don't over-focus on the formula; the point is lending adds a few percent of steady income per trade.");

// 8 RESULTS 1
s=p.addSlide(); s.background={color:WHITE};
head(s,"7","Results - the backtest, and the honest version","Raw backtest vs the selection-bias-adjusted number we'd actually plan around.");
statCard(s,0.6,1.5,3.0,"$26.3M","backtest (68% data)",MINT);
statCard(s,3.65,1.5,3.0,"$22.3M","adjusted (56% real)",NAVY);
statCard(s,6.7,1.5,3.0,"22-27%","CAGR range",NAVY);
statCard(s,9.75,1.5,3.0,"0%","chance of a 4yr loss",MINT);
s.addImage({path:`${R}/backtest_equity.png`,x:0.5,y:2.95,w:7.4,h:3.33});
const bh=(t)=>({text:t,options:{fontFace:BF,fontSize:11.5,bold:true,color:WHITE,fill:NAVY,valign:"middle",align:"center"}});
const bd=(t,o={})=>({text:t,options:{fontFace:BF,fontSize:11.5,color:INKT,valign:"middle",align:o.align||"center",...o}});
s.addTable([[{...bh("vs market (56% adj)"),options:{...bh("").options,align:"left"}},bh("$10M->"),bh("CAGR")],
 [bd("Alpha Forge (hedged)",{align:"left",bold:true,color:NAVY}),bd("$23M",{bold:true,color:MINT}),bd("22%",{bold:true})],
 [bd("Alpha Forge (un-hedged)",{align:"left"}),bd("$27M"),bd("28%")],
 [bd("S&P 500 buy & hold",{align:"left"}),bd("$17M"),bd("13%")],
 [bd("XBI biotech buy & hold",{align:"left"}),bd("$14M"),bd("10%")]],
 {x:8.15,y:3.1,w:4.6,colW:[2.4,1.1,1.1],rowH:0.5,border:{type:"solid",color:LINE,pt:1},valign:"middle"});
s.addText("Even after the honesty haircut, well ahead of the market - and it never has a losing 4-year run in the sims.",
 {x:8.15,y:5.9,w:4.6,h:0.6,fontFace:BF,fontSize:11.5,color:MUTED,italic:true,valign:"top"});
pageno(s,8);
s.addNotes("Here's the headline. The raw backtest turns $10M into $26.3M. But remember the selection-bias fix - adjust to the realistic 56% success rate and it's $22.3M. I'd lead with BOTH: 'the backtest says 26, but the honest number we'd plan around is 22.' Either way that's a 22 to 27% annual return with - and this is the part I like - zero losing four-year runs across all our simulations. The chart shows the adjusted strategy against the market: the green line, our strategy, ends around $23M hedged, $27M un-hedged, versus the S&P at $17M and biotech at $14M. So even after we haircut ourselves, we're comfortably ahead of just buying the market. One honest note on the next slide - a lot of that edge is the lending, not just the stock picking.");

// 9 RESULTS 2 (per-trade)
s=p.addSlide(); s.background={color:WHITE};
head(s,"8","Where the profit comes from - every trade","Mostly the stock (~77%), a steady slice from lending (~23%) - and we don't win them all.");
s.addImage({path:`${R}/per_trade_breakdown.png`,x:0.5,y:1.75,w:7.6,h:3.18});
const wh=(t)=>({text:t,options:{fontFace:BF,fontSize:12,bold:true,color:WHITE,fill:NAVY,valign:"middle",align:"center"}});
const wd=(t,o={})=>({text:t,options:{fontFace:BF,fontSize:12,color:INKT,valign:"middle",align:o.align||"center",...o}});
s.addTable([[{...wh("Trades"),options:{...wh("").options,align:"left"}},wh("Price"),wh("Lend"),wh("Net")],
 [wd("118 winners",{align:"left",color:MINT,bold:true}),wd("+26.4"),wd("+2.5"),wd("+28.4",{bold:true})],
 [wd("90 losers",{align:"left",color:RED,bold:true}),wd("-11.9"),wd("+1.9"),wd("-10.4",{bold:true})],
 [wd("All 208",{align:"left",bold:true,color:NAVY}),wd("+14.6"),wd("+4.3"),wd("+18.0",{bold:true,color:NAVY})]],
 {x:8.3,y:1.85,w:4.4,colW:[1.6,0.95,0.95,0.9],rowH:0.55,border:{type:"solid",color:LINE,pt:1},valign:"middle"});
s.addText([{text:"Price ~77%, lending ~23% of profit. ",options:{bold:true,color:NAVY}},
 {text:"And 90 of 208 trades LOST on price (winners that still drifted down) - lending pays on every one, cushioning them.",options:{color:INKT}}],
 {x:8.3,y:3.95,w:4.4,h:2.0,fontFace:BF,fontSize:12.5,lineSpacingMultiple:1.2,valign:"top"});
pageno(s,9);
s.addNotes("This is the 'prove it' slide for the 80/20 question. Each bar is one real trade: blue is what the stock did, gold is the lending fee. Add it all up and about 77% of the profit is the stock going up, 23% is lending. So yes - mostly stock picking, but lending is a real, meaningful chunk. Now the honest part, right column: 118 trades won, 90 LOST money on price - those are winners where the trial succeeded but the stock still drifted down. We don't win them all. Here's why lending matters beyond the 23%: it pays on every single trade regardless of what the stock does, so it steadily cushions those 90 losers. It's the seatbelt.");

// 10 ROBUSTNESS no-model + model value
s=p.addSlide(); s.background={color:WHITE};
head(s,"9","Does it even need a model?","Yes - the model roughly adds 40% over trading with zero skill.");
statCard(s,1.0,2.1,3.4,"$16.3M","NO model (long everything)",MUTED);
s.addText("->",{x:4.6,y:2.2,w:1.0,h:1.0,fontFace:HF,fontSize:36,bold:true,color:MINT,align:"center",valign:"middle"});
statCard(s,5.7,2.1,3.4,"$22.3M","WITH a 90% model",MINT);
statCard(s,9.5,2.1,3.4,"+40%","the model's value",NAVY);
s.addText([{text:"Even with zero skill - just long everything against the crowd - you make money at the realistic 56% rate, because winners still outnumber losers and lending pays. ",options:{color:INKT}},
 {text:"The model's job is to turn that floor into a real return",options:{bold:true,color:NAVY}},
 {text:" - and, crucially, to keep working when winners get rarer.",options:{color:INKT}}],
 {x:1.0,y:3.9,w:11.3,h:1.3,fontFace:BF,fontSize:15,lineSpacingMultiple:1.25,valign:"top"});
s.addShape(p.ShapeType.roundRect,{x:1.0,y:5.35,w:11.3,h:1.1,fill:{color:"F0FAF6"},line:{color:MINT,width:1},rectRadius:0.08});
s.addText([{text:"Floor $16.3M (no skill)  ·  Realistic $22.3M (90% model)  ·  Ceiling $24.9M (perfect)  -  ",options:{bold:true,color:NAVY}},
 {text:"all at the honest 56% base rate, all with 0% chance of a 4-year loss.",options:{color:INKT}}],
 {x:1.25,y:5.5,w:10.8,h:0.8,fontFace:BF,fontSize:13.5,valign:"middle"});
pageno(s,10);
s.addNotes("A fair challenge is: do you even need a fancy model, or are you just riding a rising biotech market? So we tested the dumbest possible version - no model at all, just buy EVERY catalyst and lend. Even that makes $16M at the realistic 56% rate, because winners still outnumber losers two-to-one and lending pays on all of them. Add a decent 90% model and you get to $22M - so the model is worth about 40% more. The ceiling with a perfect model is $25M. The real point: there's a positive floor even with no skill, and the model's job is to lift you off that floor AND - as the next slide shows - to protect you when winners get rarer. And all three of these never lose money over four years in the sims.");

// 11 PRECISION / BASE RATE
s=p.addSlide(); s.background={color:WHITE};
head(s,"10","The one thing that can kill it: precision","A '90% accurate' model can still be wrong half the time when winners are rare.");
s.addText("Imagine 1,000 companies, only 10% succeed. A 90%-accurate model:",{x:0.6,y:1.65,w:12,h:0.4,fontFace:BF,fontSize:14,bold:true,color:NAVY});
const ph=(t)=>({text:t,options:{fontFace:BF,fontSize:13,bold:true,color:WHITE,fill:NAVY,align:"center",valign:"middle"}});
const pd2=(t,o={})=>({text:t,options:{fontFace:BF,fontSize:13,color:INKT,align:"center",valign:"middle",...o}});
s.addTable([[{...ph(""),options:{...ph("").options}},ph("Model says SUCCESS"),ph("Model says fail")],
 [pd2("100 real winners",{bold:true,align:"left"}),pd2("90 caught",{color:MINT}),pd2("10 missed")],
 [pd2("900 real failures",{bold:true,align:"left"}),pd2("90 LANDMINES",{color:RED,bold:true}),pd2("810 avoided")]],
 {x:0.6,y:2.15,w:7.5,colW:[2.7,2.6,2.2],rowH:0.62,border:{type:"solid",color:LINE,pt:1},valign:"middle"});
s.addShape(p.ShapeType.roundRect,{x:8.35,y:2.15,w:4.35,h:1.86,fill:{color:"FBF3F2"},line:{color:RED,width:1.2},rectRadius:0.09});
s.addText("We buy 180, only 90 are real",{x:8.55,y:2.3,w:4,h:0.4,fontFace:HF,fontSize:15,bold:true,color:RED,margin:0});
s.addText("-> precision = 90/180 = 50%. Half the book is landmines that crash, even though the model is '90% accurate.'",
 {x:8.55,y:2.75,w:4,h:1.1,fontFace:BF,fontSize:13,color:INKT,valign:"top",margin:0});
s.addText([{text:"Why we're OK: ",options:{bold:true,color:MINT}},
 {text:"we trade Phase 2/3/FDA readouts, not 10%-success early drugs - our realistic base rate is ~56%, where a 90% model keeps 92% precision. But this is THE risk: the model needs high ",options:{color:INKT}},
 {text:"precision",options:{bold:true,color:NAVY}},{text:", not just accuracy.",options:{color:INKT}}],
 {x:0.6,y:4.4,w:12.1,h:1.1,fontFace:BF,fontSize:14,lineSpacingMultiple:1.2,valign:"top"});
s.addText("Precision = when the model says \"success,\" how often it's actually right. It matters because a wrong pick is longed and crashes ~15%.",
 {x:0.6,y:5.65,w:12.1,h:0.6,fontFace:BF,fontSize:12.5,color:MUTED,italic:true});
pageno(s,11);
s.addNotes("This is the most important risk slide - if you remember one caveat, it's this. 'Accuracy' can fool you. Picture 1,000 companies where only 10% win. Even a 90%-accurate model catches 90 of the 100 winners - but it also wrongly flags 90 of the 900 losers as winners. So it says 'success' to 180 names, and only half are real. That's 'precision' - half your book is landmines that crash, even though the model is technically 90% accurate. That's the classic base-rate trap. Now the good news for us - bottom line - we're NOT in a 10% world. We trade Phase 2, 3 and FDA readouts, which win about 56% of the time, and there a 90% model keeps 92% precision, so it holds up. But the message to the team building the model: chase precision, not just accuracy.");

// 12 WHAT COULD BREAK IT
s=p.addSlide(); s.background={color:WHITE};
head(s,"11","What could break it","The honest list - what we assumed, and what we can't yet know.");
const ch=(t)=>({text:t,options:{fontFace:BF,fontSize:12.5,bold:true,color:WHITE,fill:NAVY,align:"center",valign:"middle"}});
const cd=(t,o={})=>({text:t,options:{fontFace:BF,fontSize:12.5,color:INKT,align:o.align||"left",valign:"middle",...o}});
const conf=(t,c)=>({text:t,options:{fontFace:BF,fontSize:12,bold:true,color:c,align:"center",valign:"middle"}});
s.addTable([[{...ch("Assumption"),options:{...ch("").options,align:"left"}},ch("What we used"),ch("Confidence")],
 [cd("Model precision"),cd("90% acc -> 92% precision at 56%",{align:"center"}),conf("the big unknown",RED)],
 [cd("Borrow rate / utilization"),cd("100%/yr, 40% (assumed)",{align:"center"}),conf("no data - swept",RED)],
 [cd("Timing & costs"),cd("T-20/T+63, 80+5 bps",{align:"center"}),conf("grounded",MINT)],
 [cd("Market regime"),cd("all paths are 2016-2019",{align:"center"}),conf("not stress-tested",GOLD)],
 [cd("The hedge"),cd("on (optional)",{align:"center"}),conf("cost return here",GOLD)]],
 {x:0.6,y:1.75,w:12.1,colW:[4.2,4.9,3.0],rowH:0.55,border:{type:"solid",color:LINE,pt:1},valign:"middle"});
s.addShape(p.ShapeType.roundRect,{x:0.6,y:5.35,w:12.1,h:1.1,fill:{color:"FBF7EE"},line:{color:GOLD,width:1},rectRadius:0.08});
s.addText([{text:"Biggest caveat: ",options:{bold:true,color:"9A6A12"}},
 {text:"the 0%-loss result is conditional on a 2016-2019-like market - every simulated path comes from that window. A broad sector crash is a separate risk (which is what the optional hedge is for).",options:{color:INKT}}],
 {x:0.85,y:5.48,w:11.6,h:0.85,fontFace:BF,fontSize:13,valign:"middle"});
pageno(s,12);
s.addNotes("I'd rather raise our own weak spots than have someone find them. Top of the list, in red: model precision - we don't have the model yet, so that 92% is a target, not a fact. Borrow economics we assumed with no hard data, though we stress-tested a wide range. Timing and trading costs are solid. Two amber ones people miss: first, every simulation uses 2016-to-2019 price data, so when I say 'zero losing years,' that's zero losing years IN a market like that one - a real sector crash is a separate risk, and that's exactly what the optional hedge insures against. Second, the hedge itself cost us return in this friendly window. None of these are dealbreakers, but they're the honest fine print.");

// 13 SCALABILITY
s=p.addSlide(); s.background={color:WHITE};
head(s,"12","How big can it get? ~$100M","Small-cap liquidity caps it - a boutique sleeve, not a mega-fund.");
let sy=1.85; [["Only ~16-32 catalysts at once","you can't invent more small-cap readouts - the number of 'seats' is fixed"],
 ["Each stock trades ~$3.3M/day (median)","a position can only be about one day's volume before your own buying moves the price"],
 ["Position = 5% of the fund","so fund size ~ $3.3M / 5% ~ $67M; at ~2 days' volume ~ $134M"]].forEach((c,i)=>{ s.addText(String(i+1),{x:0.7,y:sy,w:0.6,h:0.6,fontFace:HF,fontSize:18,bold:true,color:WHITE,align:"center",valign:"middle",fill:{color:NAVY},rectRadius:0.3,shape:p.ShapeType.roundRect});
  s.addText(c[0],{x:1.5,y:sy-0.02,w:5.0,h:0.65,fontFace:HF,fontSize:15,bold:true,color:NAVY,valign:"middle",margin:0});
  s.addText(c[1],{x:6.7,y:sy-0.02,w:6.0,h:0.7,fontFace:BF,fontSize:13,color:INKT,valign:"middle",margin:0}); sy+=1.15; });
s.addShape(p.ShapeType.roundRect,{x:0.6,y:5.3,w:12.1,h:1.15,fill:{color:"F4F6FC"},line:{color:NAVY,width:1},rectRadius:0.08});
s.addText([{text:"Deployable ~$50-150M, call it ~$100M. ",options:{bold:true,color:NAVY}},
 {text:"Push past that and you either skip the thinnest names or pay far more to trade - the edge erodes. It's a high-return niche sleeve, not a flagship.",options:{color:INKT}}],
 {x:0.85,y:5.42,w:11.6,h:0.9,fontFace:BF,fontSize:13.5,valign:"middle"});
pageno(s,13);
s.addNotes("How much money can this actually hold? Answer: about $100M, and here's the plain logic. First, there are only ever about 16 to 32 of these catalysts happening at once - you can't manufacture more small-cap readouts, so the number of seats is fixed. Second, these stocks are tiny - the typical one only trades about $3.3M a day, and if your position gets much bigger than a day's trading, your own buying pushes the price against you. Since each position is 5% of the fund, that math lands around $67 to $134M - call it $100M. Past that you're forced to skip the smallest names or pay up to trade, and the edge bleeds away. So this is a sharp little niche fund, not the next giant - which is fine for an uncorrelated sleeve.");

// 14 RECOMMENDATION
s=p.addSlide(); s.background={color:INK};
s.addText("Recommendation",{x:0.85,y:0.7,w:11.6,h:0.8,fontFace:HF,fontSize:34,bold:true,color:WHITE,margin:0});
s.addText("The economics work. The whole bet now rides on one thing: can we build a precise enough model?",
 {x:0.87,y:1.55,w:11.6,h:0.5,fontFace:BF,fontSize:16,color:ICE,italic:true,margin:0});
let ry2=2.25; [["Proven",MINT,"Long+lend beats the market even after the honest 56% haircut ($22M, 22%, 0% loss). Lending adds ~19%. The structure has a positive floor with zero skill."],
 ["The catch",GOLD,"It all depends on model precision - at a realistic base rate a 90% model works, but precision, not accuracy, is what keeps landmines out."],
 ["Next steps",WHITE,"1) Build & validate the real model - measure precision.  2) Add a stop-loss to cut drifters and misclassified landmines.  3) Confirm borrow economics with a prime broker.  Run it as a capacity-limited (~$100M) uncorrelated sleeve."]].forEach(c=>{ s.addShape(p.ShapeType.roundRect,{x:0.85,y:ry2,w:11.6,h:1.3,fill:{color:"232C4D"},line:{color:"34406B",width:1},rectRadius:0.09});
  s.addText(c[0].toUpperCase(),{x:1.1,y:ry2+0.15,w:2.4,h:0.9,fontFace:HF,fontSize:15,bold:true,color:c[1],valign:"top",margin:0});
  s.addText(c[2],{x:3.4,y:ry2+0.15,w:8.9,h:1.0,fontFace:BF,fontSize:13,color:ICE,lineSpacingMultiple:1.15,valign:"middle",margin:0}); ry2+=1.45; });
pageno(s,14);
s.addNotes("To wrap up - the ask. The economics work: even after we haircut ourselves to the realistic 56%, long+lend makes about $22M, 22% a year, never loses over four years, and beats the market, with lending adding roughly a fifth of that. And there's a positive floor even with no skill. The catch - the entire thing now hinges on one question: can we build a model that's not just accurate but PRECISE, so we keep the landmines out. So the next steps are: actually build and validate the model and measure its precision; add a stop-loss to cut the losers and any landmines; and confirm the borrow economics with a prime broker. And we'd run it as a roughly $100M uncorrelated sleeve, not a flagship. That's the recommendation - proceed to build the model.");

p.writeFile({fileName:`${R}/Alpha_Forge_Deck.pptx`}).then(f=>console.log("WROTE",f));
