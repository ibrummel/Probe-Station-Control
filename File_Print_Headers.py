CAP_FREQ_HEADER = ('**********************************'
                   '\nMeasurement Type:\t{meas_type}'
                   '\nMeasurement Date:\t{meas_date}'
                   '\nMeasurement Time:\t{meas_time}'
                   '\n******Measurement Parameters******'
                   '\nMeasurement Number:\t{meas_num}'
                   '\nStart Frequency [Hz]:\t{start_freq}'
                   '\nStop Frequency [Hz]:\t{stop_freq}'
                   '\nImpedance Range:\t{range}'
                   '\nNumber of Points:\t{num_pts}'
                   '\nData Averaging Per Point:\t{data_averaging}'
                   '\nPer Step Delay:\t{step_delay}'
                   '\nOscillator [{osc_type}]:\t{osc}'
                   '\nDC Bias [{bias_type}]:\t{bias}'
                   '\nPre Measurement Delay (ms):\t{pre_meas_delay}'
                   '\n***********Sample Notes***********'
                   '\n{notes}'
                   '\n************End Header************\n\n')

# Note: Full header in a Cap Freq Temp measurement is built from the above for consistency.
#  Header generation replaces the "Sample Notes" separator line with the formatted version
#  of the following string.
CAP_FREQ_TEMP_ADDON = ('\n*************Thermal*************'
                       '\nTemp Control Device:\t{temp_device}'
                       '\nRamp Rate:\t{ramp}'
                       '\nDwell Before Measurement:\t{dwell}'
                       '\nStabilization Measurement Interval:\t{stab_int}'
                       '\nUser Probe Average T [°C]:\t{user_avg}'
                       '\nUser Probe Std. Deviation [°C]:\t{user_stdev}'
                       '\nChamber Probe Average T [°C]:\t{chamber_avg}'
                       '\nChamber Probe Std. Deviation [°C]:\t{chamber_stdev}'
                       '\nImpedance Value Standard Deviation [Ohm]:\t{z_stdev}'
                       '\n***********Sample Notes***********')
