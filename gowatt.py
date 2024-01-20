name = "gowatt"

'''
Gowatt
======
Gowatt is a layered client API designed to access and control Growatt SPA/SPH series
Inverters and A/C Couplers.

It automatically goes through a list of growatt.com servers until login is
successful.  This can be overridden when connecting.

It uses a layered cache with a half-life of the SPA/SPH's Shine Adapters poll
time.  This ensures that excessive requests to the Growatt Servers are limited.

All non-time based raw data functions store in the cache on-demand.  All highlevel
functions use the cached data.

The idea of having a raw API that maps 1:1 to the Growatt Server, and a highlevel API
is to allow for abstraction, and some client stability.  Whether you use the raw or
highlevel functions is based entirely on whether you need stability or variable not
provided at the high level.

This code is inspired by https://github.com/indykoning/PyPi_GrowattServer
Tested on an SPA3000.  Dom3442 provided SPH3600 information (Mix).
'''

from random import randint
from datetime import datetime
from time import time

import json
import requests

class Gowatt(object):  
  '''
  Class Variables
  '''
  server_urls = [
    'server.growatt.com',
    'server-api.growatt.com',
    'openapi.growatt.com'
  ]
  server_url        = None
  agent_identifier  = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.81"
  username          = None # needed for relogging in on timeout
  password          = None # needed for relogging in on timeout
  session           = None
  plantId           = None
  deviceType        = None
  deviceSN          = None
  datalogSN         = None
  dataCache         = {}
  refreshTime       = 1 # time in minutes before data expires 

  def __init__(self, add_random_user_id=False, agent_identifier=None, server_urls=None):
    '''
    Init the object
    '''
    if (agent_identifier != None):
      # replace the agent if needed
      self.agent_identifier = agent_identifier

    if (server_urls != None):
      # replace server list  
      self.server_urls = server_urls
          
    if (add_random_user_id):
      # add random user id at end of agent_identifier
      random_number = ''.join(["{}".format(randint(0,9)) for num in range(0,5)])
      self.agent_identifier += " - " + random_number

    self.session = requests.Session()
    
    # for debug
    # self.session.hooks = {
    #   'response': lambda response, *args, **kwargs: response.raise_for_status()
    # }

    headers = {
      'User-Agent': self.agent_identifier
    }

    self.session.headers.update(headers)

  def getBatteryRate(self):
    '''
    Returns battery rate in Watt Hours as an integer
    Battery is positive +Wh if discharging (power out), and negative -Wh (power in) if charging
    '''
    device = self.rawGetStatusData()
    if not device: return None
    
    # convert to Wh
    # Battery:  positive for power out, negative for power in if charging battery
    charge = float(device['chargePower']) * -1000

    if charge == 0:
      charge = float(device['pdisCharge1']) * 1000

    return 0 if device == None else int(charge)

  def getBatteryLevel(self):
    '''
    Returns battery level is a percentage integer
    '''  
    device = self.rawGetStatusData()
    if not device: return None

    return 0 if device == None else int(device['SOC'])

  def getDataLogSN(self):
    return self.datalogSN
  
  def getDeviceSN(self):
    return self.deviceSN

  def getDeviceType(self):
    return self.deviceType

  def getGridRate(self):
    '''
    Returns FROM grid in Watt Hours as an integer
    Positive for power out (to local/house), negative for power in (to grid)
    '''
    device = self.rawGetStatusData()
    if not device: return None
    
    # convert to Wh
    # Solar:    positive for power out
    # Battery:  positive for power out, negative for power in if charging battery
    # Local:    negative as power in
    # Grid:     positive for power out (to local/house), negative for power in (to grid)

    grid = float(device['pactogrid']) * 1000
    
    if grid == 0:
      # if not positive, the local/house plus battery drain minus solar
      # should equal what's coming FROM the grid or TO the grid

      local = float(device['pLocalLoad']) * -1000
      battery = self.getBatteryRate() # positive for discharging (power out)
      solar = self.getSolarRate() # positive for power out

      grid = local + battery + solar
    
    # Grid: positive for power out (to local/house), negative for power in (to grid)
    return -grid

  def getLocalLoad(self):
    '''
    Returns local load to local/house in Watt Hours as an integer
    Local load is negative (-Wh) as power in being consumed/used
    
    '''
    device = self.rawGetStatusData()
    if not device: return None
    
    battery = self.getBatteryRate()
    if battery > 0: battery = 0 # remove impact if not helping load
    
    grid = float(device['pactogrid']) * -1000
    if grid < 0: grid = 0 # remove impact if not helping load
    
    # convert to Wh
    # Local:    negative as power in
    return (-float(device['pLocalLoad']) * 1000) + battery + grid
  
  def getPlantId(self):
    return self.plantId
  
  def getSolarRate(self):
    '''
    Returns ppv in Watt Hours as an integer
    Positive Wh as power out
    '''
    device = self.rawGetStatusData()
    if not device: return None
    
    # convert to Wh
    # Solar:    positive for power out
    return float(device['ppv']) * 1000
      
  def login(self, username, password):
    '''
    Log the user in.  This grabs critical data needed later:
      plantId
      deviceSN
      datalogSN

    Returns
      True - if logged in and ready
    '''

    loaded = False
    self.username = username # save for relogin
    self.password = password # save for relogin

    for url in self.server_urls:
      self.server_url = 'https://' + url + '/'
      
      try:
        self.session.cookies.clear()
        data =  self.post(
                  'login',  # page
                  formData = {
                    'account': username,
                    'password': password
                  },
                  cached = False,
                  retry = False
                )
      except:
        continue

      if data == None: continue

      self.plantId = self.session.cookies.get('onePlantId')
      
      data =  self.rawGetDevices()
      if data == None: continue
      
      # TODO: can support multiple devices here - if needed
      self.deviceType = data[0]['deviceTypeName']
      self.deviceSN = data[0]['sn']
      self.datalogSN = data[0]['datalogSn']
      
      data = self.rawGetDataLoggerInfo()
      if data:
        # update cache with real refresh time  
        self.refreshTime = int(data['interval']) / 2 # half actual so we don't drift past
        for item in self.dataCache:
          self.dataCache[item]['TTL'] = int(time()) + self.refreshTime
      
      loaded = True
      break
    
    return loaded
  
  def post(self, page, args = {}, formData = {}, cached = True, retry = True):
    '''
    Simple helper function to get data
    '''
    
    if cached == True:
      lut = page + ':' + str(args) + ':' + str(formData)
      if lut in self.dataCache:
        # check cache to see if timed out
        if self.dataCache[lut]['TTL'] > int(time()):
          # return cache rather than request again  
          return self.dataCache[lut]['obj']
      
    attributes = ''
    for arg in args:
      attributes += '?' if len(attributes) == 0 else '&'
      attributes += arg + '=' + args[arg]
    
    try:
      success = False
      while not success:
        response = self.session.post(
                      self.server_url + page + attributes,
                      data = formData
                    )
      
        if not response.ok: return None
        if not response.content: return None

        content = str(response.content)
        success = (content.find('<!DOCTYPE html') == -1)
        
        if not success:
          # happens if we get logged out - no longer a JSON response
          if retry:
            logged_in = self.login(self.username,self.password)
            if not logged_in: return None
          else:
            return None

      data = json.loads(response.content.decode('utf-8'))

    except:
      # fatal failure
      return None  

    if not 'result' in data: return data
    if data['result'] != 1: return None
    if not 'obj' in data: return data

    if cached == True:
      self.dataCache[lut] = {
        'TTL': int(time()) + (self.refreshTime * 60),
        'obj': data['obj']
      }

    return self.dataCache[lut]['obj']

  def rawGetDataLoggerInfo(self):
    return  self.post(
              'panel/getDeviceInfo',
              formData = {
                'plantId': self.plantId,
                'deviceTypeName': 'datalog',
                'sn': self.datalogSN
              }
            )
  
  def rawGetDevices(self):
    data =  self.post(
              'panel/getDevicesByPlantList',
              formData = {
                'currPage': '1',
                'plantId': self.plantId
              }
            )
    if 'datas' in data:
      return data['datas']
    return data

  def rawGetEicDevices(self):
    return  self.post(
              'panel/getEicDevicesByPlant',
              formData = { 'plantId': self.plantId }
            )
  
  def rawGetPlantData(self):
    return  self.post(
              'panel/getPlantData',
              args = { 'plantId': self.plantId }
            )
  
  def rawGetStatusData(self):
    return  self.post(
              'panel/{}/get{}StatusData'.format(self.deviceType,self.deviceType.upper()),
              args = { 'plantId': self.plantId },
              formData = { '{}Sn'.format(self.deviceType): self.deviceSN }
            )
  
  def rawGetBatChart(self,date = datetime.today().strftime('%Y-%m-%d')):
    return  self.post(
              'panel/{}/get{}BatChart'.format(self.deviceType,self.deviceType.upper()),
              formData = {
                'plantId': self.plantId,
                '{}Sn'.format(self.deviceType): self.deviceSN,
                'date': date
              }
            )

  def rawGetEnergyDayChart(self,date = datetime.today().strftime('%Y-%m-%d')):
    return  self.post(
              'panel/{}/get{}EnergyDayChart'.format(self.deviceType,self.deviceType.upper()),
              formData = {
                'plantId': self.plantId,
                '{}Sn'.format(self.deviceType): self.deviceSN,
                'date': date
              }
            )

  def rawGetEnergyMonthChart(self,date = datetime.today().strftime('%Y-%m')):
    return  self.post(
              'panel/{}/get{}EnergyMonthChart'.format(self.deviceType,self.deviceType.upper()),
              formData = {
                'plantId': self.plantId,
                '{}Sn'.format(self.deviceType): self.deviceSN,
                'date': date
              }
            )

  def rawGetEnergyYearChart(self,year = datetime.today().strftime('%Y')):
    return  self.post(
              'panel/{}/get{}EnergyYearChart'.format(self.deviceType,self.deviceType.upper()),
              formData = {
                'plantId': self.plantId,
                '{}Sn'.format(self.deviceType): self.deviceSN,
                'year': year
              }
            )
  
  def rawGetEnergyTotalChart(self,year = datetime.today().strftime('%Y')):
    return  self.post(
              'panel/{}/get{}EnergyTotalChart'.format(self.deviceType,self.deviceType.upper()),
              formData = {
                'plantId': self.plantId,
                '{}Sn'.format(self.deviceType): self.deviceSN,
                'year': year
              }
            )

  def rawSetInternal(self, type, common, values):
    '''
    Applies settings for specified system based on serial number

    Arguments:
      type      Setting to be configured (str)
      common    Set of parameters for the setting call (dict)
      values    Parameters to be sent to the system (dict or list of str)
                (array which will be converted to a dictionary)

    Returns:
      JSON response from the server whether the configuration was successful
    '''
    settings = values
        
    # If we've been passed an array then convert it into a dictionary
    if isinstance(values, list):
        settings = {}
        for index, param in enumerate(values, start=1):
            settings['param' + str(index)] = param
        
    parameters = {**common, **settings}

    return self.post(
            'tcpSet.do', 
            formData = parameters,
            cached = False
           )

  def rawSet(self, type, settings):
    common = {
      'action': '{}Set'.format(self.deviceType),
      'serialNum': self.deviceSN,
      'type': type
    }
    
    return self.rawSetInternal(type, common, settings) 
  
  def setRuleBatteryFirst(self,amount,startHour,endHour,enable):
    '''
    Sets the amount to charge the battery.
    Only the first schedule is used, all others are zero'd
    
    Parameters:
      amount    -> percentage to charge battery to
      startHour -> when to start
      endHour   -> when to finish
      enable    -> whether rule is enabled or disabled
    '''  
    # All parameters need to be given, including zeros
    # All parameters must be strings
    schedule_settings = [
      '100',                        # Charging power %
      str(amount),                  # Stop charging when above SoC %
      str(startHour), '00',         # Schedule 1 - Start time
      str(endHour), '00',           # Schedule 1 - End time
      str('1' if enable else '0'),  # Schedule 1 - Enabled/Disabled (1 = Enabled)
      '00','00',                    # Schedule 2 - Start time
      '00','00',                    # Schedule 2 - End time
      '0',                          # Schedule 2 - Enabled/Disabled (1 = Enabled)
      '00','00',                    # Schedule 3 - Start time
      '00','00',                    # Schedule 3 - End time
      '0'                           # Schedule 3 - Enabled/Disabled (1 = Enabled)
    ]
    
    if self.deviceType == 'mix':
      # same as 'spa' but needs to enable AC charging (index 2 - between amount and start)
      schedule_settings.insert(2,str('1' if enable else '0'))

    response = self.rawSet('{}_ac_charge_time_period'.format(self.deviceType),schedule_settings)
    print(json.dumps(response)) # used to show working
    
    if not response or not 'msg' in response: return False

    if response['msg'] != 'inv_set_success':
      print('failed - NEED RECOVERY - ' + response['msg'])
      return False      

    return True

  def setRuleLoadFirst(self,startHour,endHour,enable):
    '''
    Sets the time to use load.
    Only the first schedule is used, all others are zero'd
    
    Parameters:
      startHour -> when to start
      endHour   -> when to finish
      enable    -> whether rule is enabled or disabled
    '''
    
    # All parameters need to be given, including zeros
    # All parameters must be strings
    schedule_settings = [
      str(startHour), '00',         # Schedule 1 - Start time
      str(endHour), '00',           # Schedule 1 - End time
      str('1' if enable else '0'),  # Schedule 1 - Enabled/Disabled (1 = Enabled)
      '00','00',                    # Schedule 2 - Start time
      '00','00',                    # Schedule 2 - End time
      '0',                          # Schedule 2 - Enabled/Disabled (1 = Enabled)
      '00','00',                    # Schedule 3 - Start time
      '00','00',                    # Schedule 3 - End time
      '0'                           # Schedule 3 - Enabled/Disabled (1 = Enabled)
    ]
    
    if self.deviceType == 'mix':
      # same as 'spa' but needs to enable AC charging (index 2 - between amount and start)
      schedule_settings.insert(2,str('1' if enable else '0'))

    response = self.rawSet('{}_load_flast'.format(self.deviceType),schedule_settings)
    print(json.dumps(response)) # used to show working
    
    if not response or not 'msg' in response: return False

    if response['msg'] != 'inv_set_success':
      print('failed - NEED RECOVERY - ' + response['msg'])
      return False

    return True
  
  def setTime(self,hour,min,date = datetime.today().strftime('%Y-%m-%d')):
    '''
    Sets the system time.
    
    Parameters:
      hour -> to set
      min  -> to set
      date -> override today's date (prob not needed)
    '''  

    settings = [
      '{} {}:{}'.format(date,hour,min)
    ]
    
    response = self.rawSet('pf_sys_year',settings)
    print(json.dumps(response)) # used to show working
    
    if not response or not 'msg' in response: return False

    if response['msg'] != 'inv_set_success':
      print('failed - NEED RECOVERY - ' + response['msg'])
      return False      

    return True
