import gowatt

if __name__ == '__main__':  
  session = gowatt.Gowatt();
  
  print('Logging into Growatt')
  success = session.login('username','12345678')
  if not success:
    print('Failed to log into server')
    quit()
    
  print('Success.')
  
  plantId = session.getPlantId();
  deviceSN = session.getDeviceSN();
  datalogSN = session.getDataLogSN();
  print('Plant ID:',plantId,'\nDevice SN:',deviceSN,'\nDataLog SN:',datalogSN)

  # Example using raw function
  device = session.rawGetSPAstatusData()
  if device:
    print('raw test')
    capacity = int(device['SOC']) - 10
    schedule_settings = ['100',                       # Charging power %
                          str(capacity),              # Stop charging when above SoC %
                          '01', '00',                 # Schedule 1 - Start time
                          '08', '00',                 # Schedule 1 - End time
                          '1',                        # Schedule 1 - Enabled/Disabled (1 = Enabled)
                          '00','00',                  # Schedule 2 - Start time
                          '00','00',                  # Schedule 2 - End time
                          '0',                        # Schedule 2 - Enabled/Disabled (1 = Enabled)
                          '00','00',                  # Schedule 3 - Start time
                          '00','00',                  # Schedule 3 - End time
                          '0']                        # Schedule 3 - Enabled/Disabled (1 = Enabled)
    response = session.rawSetSPA('spa_ac_charge_time_period',schedule_settings)
    print('raw test result:',str(response))

  # Example using highlevel functions
  print('highlevel test')
  capacity = session.getBatteryLevel()
  pCharge = session.getBatteryChargeRate()
  success = session.setRuleBatteryFirst(capacity - 20,1,8,True)
  print('capacity:',capacity,'%   charge rate:',pCharge,'Wh')
  print('highlevel test','passed' if success else 'failed')

