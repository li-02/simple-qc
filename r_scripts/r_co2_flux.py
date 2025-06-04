"""
CO2通量的R处理脚本
"""
from r_scripts import robjects

# 定义R函数
robjects.r("""
  library(REddyProc)
  library(dplyr)

  r_co2_flux <- function(file_name, longitude, latitude, timezone, flux_data, indicators){
      
      # start a new edd work
      flux_data$VPD<-fCalcVPDfromRHandTair(rH=flux_data$rH,Tair=flux_data$Tair)
      datanames<-colnames(flux_data)
      EddyProc.C<-sEddyProc$new(ID=file_name, Data=flux_data, ColNames=datanames[-1])
      EddyProc.C$sSetLocationInfo(LatDeg=latitude,LongDeg=longitude,TimeZoneHour=timezone)
      rm(datanames)
        
      # estimate u star threshold (only co2_flux need u star threshold)
      uStarTh<-EddyProc.C$sEstUstarThold(TempColName="Tair", UstarColName="u__threshold_limit") # MPT
      select(uStarTh, -seasonYear)
      uStarThAnnual<-usGetAnnualSeasonUStarMap(uStarTh)
      uStarSuffixes<-colnames(uStarThAnnual)[-1]

      # gap filling
      EddyProc.C$sMDSGapFillAfterUstar(fluxVar="NEE",uStarVar="u__threshold_limit",uStarTh=uStarThAnnual,uStarSuffix=uStarSuffixes,FillAll=TRUE)
      
      # grep can remove
      grep("NEE_.*_f$",names(EddyProc.C$sExportResults()),value=TRUE)
      grep("NEE_.*_fsd$",names(EddyProc.C$sExportResults()),value=TRUE)
      for(i in indicators){
        EddyProc.C$sMDSGapFill(i,FillAll=TRUE)
      }
      EddyProc.C$sMDSGapFill("Tair",FillAll=FALSE) 
      # EddyProc.C$sMDSGapFill("Tsoil",FillAll=FALSE)
      EddyProc.C$sMDSGapFill("VPD",FillAll=FALSE)
      EddyProc.C$sMDSGapFill("Rg",FillAll=FALSE)

      # partitioning
      EddyProc.C$sMRFluxPartition(Suffix=uStarSuffixes) # Nighttime-based algorithm
      grep("GPP.*_f$|Reco",names(EddyProc.C$sExportResults()),value=TRUE)

      # bind the data      
      FilledEddyData.F<-EddyProc.C$sExportResults()
      CombinedData.F<-cbind(flux_data, FilledEddyData.F)

      return(CombinedData.F)
  }
""")