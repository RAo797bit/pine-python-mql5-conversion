//+------------------------------------------------------------------+
//|                                              ATR_Trailing_Stop.mq5|
//| MQL5 port of pine/ATR_Trailing_Stop.pine (demo).                  |
//|                                                                   |
//| Same rules as the Pine and Python versions:                       |
//|   nLoss = mult * SMA(true range, atrLen)                          |
//|   stop  = ratchets up under price in an uptrend, down over price  |
//|           in a downtrend, and flips when price closes through it  |
//|   buy   = close crosses above the stop, sell = crosses below      |
//| True range is averaged with a simple SMA (same as Pine's          |
//| ta.sma(ta.tr(true), n) and MT5's iATR).                           |
//+------------------------------------------------------------------+
#property copyright "Demo"
#property version   "1.00"
#property indicator_chart_window
#property indicator_buffers 4
#property indicator_plots   3

#property indicator_label1  "Trailing stop"
#property indicator_type1   DRAW_LINE
#property indicator_color1  clrDodgerBlue
#property indicator_width1  2

#property indicator_label2  "Buy"
#property indicator_type2   DRAW_ARROW
#property indicator_color2  clrLime
#property indicator_width2  2

#property indicator_label3  "Sell"
#property indicator_type3   DRAW_ARROW
#property indicator_color3  clrRed
#property indicator_width3  2

input int    InpATRLength = 14;    // ATR length
input double InpMult      = 3.0;   // ATR multiplier

double g_stop[];
double g_buy[];
double g_sell[];
double g_tr[];

//+------------------------------------------------------------------+
int OnInit()
{
   if(InpATRLength < 1 || InpMult <= 0.0)
   {
      Print("ATR_Trailing_Stop: invalid inputs");
      return INIT_PARAMETERS_INCORRECT;
   }

   SetIndexBuffer(0, g_stop, INDICATOR_DATA);
   SetIndexBuffer(1, g_buy,  INDICATOR_DATA);
   SetIndexBuffer(2, g_sell, INDICATOR_DATA);
   SetIndexBuffer(3, g_tr,   INDICATOR_CALCULATIONS);

   PlotIndexSetInteger(1, PLOT_ARROW, 233);   // up arrow
   PlotIndexSetInteger(2, PLOT_ARROW, 234);   // down arrow
   for(int p = 0; p < 3; p++)
      PlotIndexSetDouble(p, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetInteger(0, PLOT_DRAW_BEGIN, InpATRLength);

   IndicatorSetString(INDICATOR_SHORTNAME, StringFormat("ATR Trailing Stop (%d, %.1f)", InpATRLength, InpMult));
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
{
   if(rates_total < InpATRLength) return 0;

   int start = (prev_calculated > 0) ? prev_calculated - 1 : 0;

   for(int i = start; i < rates_total; i++)
   {
      g_buy[i]  = EMPTY_VALUE;
      g_sell[i] = EMPTY_VALUE;

      // true range (first bar has no previous close)
      if(i == 0)
         g_tr[i] = high[i] - low[i];
      else
         g_tr[i] = MathMax(high[i] - low[i], MathMax(MathAbs(high[i] - close[i - 1]), MathAbs(low[i] - close[i - 1])));

      if(i < InpATRLength - 1)
      {
         g_stop[i] = EMPTY_VALUE;      // Pine: na until the SMA has enough bars
         continue;
      }

      double sum = 0.0;
      for(int k = i - InpATRLength + 1; k <= i; k++) sum += g_tr[k];
      double atr   = sum / InpATRLength;
      double nLoss = InpMult * atr;

      double src      = close[i];
      double src1     = (i > 0) ? close[i - 1] : EMPTY_VALUE;
      double stop1    = (i > 0) ? g_stop[i - 1] : EMPTY_VALUE;
      bool   stop1na  = (stop1 == EMPTY_VALUE);
      double prevStop = stop1na ? src : stop1;                    // nz(stop[1], src)

      if(src > prevStop && src1 != EMPTY_VALUE && src1 > prevStop)
         g_stop[i] = MathMax(prevStop, src - nLoss);
      else if(src < prevStop && src1 != EMPTY_VALUE && src1 < prevStop)
         g_stop[i] = MathMin(prevStop, src + nLoss);
      else if(src > prevStop)
         g_stop[i] = src - nLoss;
      else
         g_stop[i] = src + nLoss;

      if(i > 0 && !stop1na)
      {
         if(src > g_stop[i] && src1 <= stop1) g_buy[i]  = low[i]  - 0.25 * atr;   // ta.crossover
         if(src < g_stop[i] && src1 >= stop1) g_sell[i] = high[i] + 0.25 * atr;   // ta.crossunder
      }
   }
   return rates_total;
}
//+------------------------------------------------------------------+
