# gowatt
Python class for managing Growatt server sessions.<br/>

Gowatt is a layered client API designed to access and control Growatt SPA/SPH series
Inverters and A/C Couplers.<br/>

It automatically goes through a list of growatt.com servers until login is
successful.  This can be overridden when connecting.<br/>

It uses a layered cache with a half-life of the SPA/SPH's Shine Adapters poll
time.  This ensures that excessive requests to the Growatt Servers are limited.<br/>

All non-time based raw data functions store in the cache on-demand.  All highlevel
functions use the cached data.<br/>

The idea of having a raw API that maps 1:1 to the Growatt Server, and a highlevel API
is to allow for abstraction, and some client stability.  Whether you use the raw or
highlevel functions is based entirely on whether you need stability or variable not
provided at the high level.<br/>

This code is inspired by https://github.com/indykoning/PyPi_GrowattServer<br/>
Tested on an SPA3000.  Dom3442 provided SPH3600 information (Mix).<br/>

# API
```
gowatt(add_random_user_id=False, agent_identifier=None, server_urls=None)
  add_random_user_id = True -> alter the agent_identifier if you have problems
  agent_identifier          -> currently reports it the Brave webbrowser
  server_urls               -> list of additional servers to check (without https://)
All args are OPTIONAL
```

```
login(username,password)
  username = 'firstSecond'
  password = '12345678'
Returns True if logged in.  At this point the PlantId, DeviceSN and DatalogSN are known,
as well as the cache expiry time; this half the datalog interval.
```

The following raw functions are currently implemented, where appropriate today's date is used, and the first deviceSN, if not specified, and return various object dicts:<br/>

```
  rawGetDataLoggerInfo(deviceSN = None)
  rawGetDevices()
  rawGetEicDevices()
  rawGetPlantData()
  rawGetStatusData(deviceSN = None)
  rawGetBatChart(date = '2023-10-08', deviceSN = None)
  rawGetEnergyDayChart(date = '2023-10-08', deviceSN = None)
  rawGetEnergyMonthChart(date = '2023-10', deviceSN = None)
  rawGetEnergyYearChart(self,year = '2023', deviceSN = None)
  rawGetEnergyTotalChart(self,year = '2023', deviceSN = None)
  rawSet(type, settings, deviceSN = None)
```

The highlevel API is a work in progress and added as needed.  It is a normalised version of the base data.  Where appropriate, if you don't specify a deviceSN then the first device is used.<br/>

```
  getBatteryRate(deviceSN = None)
    Returns battery charge/discharge rate in Watt Hours as an integer

  getBatteryLevel(deviceSN = None)
    Returns battery level is a percentage integer

  getDataLogSN(deviceSN = None)
    Return the data logger serial number discovered at login

  getDeviceSNlist()
    Return a list of known device serial numbers.  This can be used as the deviceSN argument on other APIs.

  getDeviceType(deviceSN = None)
    Return the device type.  Typically 'spa' or 'mix'.

  getGridRate(deviceSN = None)
    Returns FROM grid in Watt Hours as an integer
    A negative number means TO the grid

  getLocalLoad(deviceSN = None)
    Returns local load to house in Watt Hours as an integer

  getPlantId()
    Return the plant id discovered at login

  getSolarRate(deviceSN = None)
    Returns ppv in Watt Hours as an integer

  setRuleBatteryFirst(amount,startHour,endHour,enable,startMin = 0,endMin = 0,deviceSN = None):
    Sets the amount to charge the battery.
    Only the first schedule is used, all others are zero'd
    
    Parameters:
      amount    -> percentage to charge battery to
      startHour -> when to start
      endHour   -> when to finish
      enable    -> whether rule is enabled or disabled

    Optional:
      startMin  -> when to start by minute
      endMin    -> when to end by minute
      deviceSN  -> device serial number

  setRuleLoadFirst(self,startHour,endHour,enable,startMin = 0,endMin = 0,deviceSN = None):
    Sets the time to use load.
    Only the first schedule is used, all others are zero'd
  
    Parameters:
      startHour -> when to start
      endHour   -> when to finish
      enable    -> whether rule is enabled or disabled

    Optional:
      startMin  -> when to start by minute
      endMin    -> when to end by minute
      deviceSN  -> device serial number
```

# Example
Very little is needed to get back data.

```
import gowatt

if __name__ == '__main__':  
  session = gowatt.Gowatt();
  
  print('Logging into Growatt')
  success = session.login('username','12345678')
  if not success:
    print('Failed to log into server')
    quit()
    
  print('Success.')
  
  plantId = session.getPlantId()
  print('Plant ID:',plantId)

  deviceSNlist = session.getDeviceSNlist();

  for deviceSN in deviceSNlist:
    deviceType = session.getDeviceType(deviceSN = deviceSN)
    datalogSN = session.getDataLogSN(deviceSN = deviceSN)
    print(
      '\nDevice Type:',deviceType,
      '\nDevice SN:',deviceSN,
      '\nDataLog SN:',datalogSN
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
    capacity = int(deviceStatus['SOC']) - 10
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

  success = session.setRuleBatteryFirst(battery_level - 20,1,8,True)
  print(
    '\nbattery level:',battery_level,'%',
    '\nbattery rate:',battery,'Wh'
    '\nsolar rate:',solar,'Wh'
    '\nlocal rate:',local,'Wh'
    '\ngrid rate:',grid,'Wh'
  )
  print('highlevel test','passed' if success else 'failed')
```
