"""
光合有效辐射插补的R脚本
"""
from r_scripts import robjects

# 定义R函数
robjects.r("""
  library(REddyProc)
  library(dplyr)

  r_gap_fill_par <- function(file_name, longitude, latitude, timezone, flux_data){

      # start a new edd work
      flux_data$VPD<-fCalcVPDfromRHandTair(rH=flux_data$rH, Tair=flux_data$Tair)
      datanames<-colnames(flux_data)
      EddyProc.C<-sEddyProc$new(ID=file_name, Data=flux_data, ColNames=datanames[-1])
      EddyProc.C$sSetLocationInfo(LatDeg=latitude,LongDeg=longitude,TimeZoneHour=timezone)
      rm(datanames)

      # gap filling par
      EddyProc.C$sMDSGapFill("Par",FillAll=TRUE)

      # bind the data      
      FilledEddyData.F<-EddyProc.C$sExportResults()
      CombinedData.F<-cbind(flux_data, FilledEddyData.F)

      return(CombinedData.F)
  }
""")