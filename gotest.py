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
  print('Plant ID: {}\n'.format(plantId))

  devicesSN = session.getDeviceSNlist();

  for deviceSN in devicesSN:
    deviceType = session.getDeviceType(deviceSN);
    datalogSN = session.getDataLogSN(deviceSN);
    print(
      'Device Type: {}\nDevice SN: {}\nDatalog SN: {}'
        .format(deviceType,deviceSN,datalogSN)
    )

  # Example using raw function
  deviceInfo = session.rawGetDataLoggerInfo()
  print('\nrawGetDataLoggerInfo()\n',str(deviceInfo))

  devices = session.rawGetDevices()
  print('\nrawGetDevices()\n',str(devices))
  
  eicDevices = session.rawGetEicDevices()
  print('\nrawGetEicDevices()\n',str(eicDevices))
  
  plantData = session.rawGetPlantData()
  print('\nrawGetPlantData()\n',str(plantData))
  
  deviceStatus = session.rawGetStatusData()
  print('\nrawGetStatusData()\n',str(deviceStatus))
  
  batChart = session.rawGetBatChart()
  print('\nrawGetBatChart()\n',str(batChart))

  energyDayChart = session.rawGetEnergyDayChart()
  print('\nrawGetEnergyDayChart()\n',str(energyDayChart))
  
  energyMonthChart = session.rawGetEnergyMonthChart()
  print('\nrawGetEnergyMonthChart()\n',str(energyMonthChart))
  
  energyYearChart = session.rawGetEnergyYearChart()
  print('\nrawGetEnergyYearChart()\n',str(energyYearChart))
  
  energyTotalChar = session.rawGetEnergyTotalChart()
  print('\nrawGetEnergyTotalChart()\n',str(energyTotalChar))
  
  if deviceStatus:
    print('\nraw test')
    capacity = int(deviceStatus['SOC']) + 10
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
    if session.getDeviceType() == 'mix':
      # enable a/c charger
      schedule_settings.insert(2,'1')

    response = session.rawSet('{}_ac_charge_time_period'.format(session.getDeviceType()),schedule_settings)
    print('raw test result:',str(response))

  # Example using highlevel functions
  print('highlevel test')
  battery_level = session.getBatteryLevel()
  battery = session.getBatteryRate()
  local = session.getLocalLoad()
  solar = session.getSolarRate()
  grid = session.getGridRate()

  success = session.setRuleBatteryFirst(battery_level + 20,1,8,True)

  success = session.setRuleLoadFirst(19,20,False)

  print(
    '\nbattery level:',battery_level,'%',
    '\nbattery rate:',battery,'Wh'
    '\nsolar rate:',solar,'Wh'
    '\nlocal rate:',local,'Wh'
    '\ngrid rate:',grid,'Wh'
  )
  print('highlevel test','passed' if success else 'failed')

