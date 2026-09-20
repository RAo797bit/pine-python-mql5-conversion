//+------------------------------------------------------------------+
//|                                        Export_ATRStop_Values.mq5 |
//| Script: dumps OHLC and the ATR_Trailing_Stop values to a CSV so  |
//| tools/compare_with_mt5.py can check the Python port against real |
//| MT5 output on the same bars.                                     |
//|                                                                  |
//| Setup: compile ATR_Trailing_Stop.mq5 so ATR_Trailing_Stop.ex5    |
//| sits in MQL5\Indicators, then drag this script onto a chart.     |
//| Output: MQL5\Files\atr_stop_export.csv                           |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

input int    InpATRLength = 14;
input double InpMult      = 3.0;
input int    InpBars      = 2000;
input string InpFileName  = "atr_stop_export.csv";

void OnStart()
{
   int handle = iCustom(_Symbol, _Period, "ATR_Trailing_Stop", InpATRLength, InpMult);
   if(handle == INVALID_HANDLE)
   {
      Print("Export: could not create indicator handle, error ", GetLastError());
      return;
   }

   // wait for the indicator to finish calculating
   int tries = 0;
   while(BarsCalculated(handle) < InpBars && tries < 50)
   {
      Sleep(100);
      tries++;
   }

   MqlRates rates[];
   int got = CopyRates(_Symbol, _Period, 0, InpBars, rates);     // oldest -> newest
   double stop[];
   if(got <= 0 || CopyBuffer(handle, 0, 0, got, stop) != got)
   {
      Print("Export: could not copy rates/buffer, error ", GetLastError());
      IndicatorRelease(handle);
      return;
   }

   int fh = FileOpen(InpFileName, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(fh == INVALID_HANDLE)
   {
      Print("Export: could not open file, error ", GetLastError());
      IndicatorRelease(handle);
      return;
   }

   FileWrite(fh, "time", "open", "high", "low", "close", "stop");
   for(int i = 0; i < got; i++)
   {
      string s = (stop[i] == EMPTY_VALUE) ? "" : DoubleToString(stop[i], _Digits + 2);
      FileWrite(fh, TimeToString(rates[i].time, TIME_DATE | TIME_MINUTES),
                DoubleToString(rates[i].open,  _Digits), DoubleToString(rates[i].high, _Digits),
                DoubleToString(rates[i].low,   _Digits), DoubleToString(rates[i].close, _Digits), s);
   }
   FileClose(fh);
   IndicatorRelease(handle);
   PrintFormat("Export: wrote %d bars to MQL5\\Files\\%s", got, InpFileName);
}
//+------------------------------------------------------------------+
