# -*- coding: utf-8 -*-
#  Copyright 2018 NTT Communications
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# $Date: 2018-10-06 20:12:33 +0900 (Sat, 06 Oct 2018) $
# $Rev: 1420 $
# $Ver: $
# $Author: $

import os,time,traceback
import Common
from WebApp import WebApp,with_reconnect
from robot.libraries.BuiltIn import BuiltIn
from robot.libraries.BuiltIn import RobotNotRunningError
from selenium import webdriver
from selenium.webdriver.common.proxy import Proxy, ProxyType
import robot.libraries.DateTime as DateTime



class Arbor(WebApp):
    """ A library provides functions to control Arbor application

    The library utilize `SeleniumLibrary` and adds more functions to control
    Arbor application easily.

    See [./WebApp.html|WebApp] for common keywords of web applications.

    `SeleniumLibrary` keywords still could be used along with this library.
    See [http://robotframework.org/SeleniumLibrary/SeleniumLibrary.html|SeleniumLibrary] for more details.

    *Notes*: From 0.1.10, move from `Selenium2Library` to `SeleniumLibrary`
    """

    ROBOT_LIBRARY_SCOPE = 'TEST SUITE'
    ROBOT_LIBRARY_VERSION = Common.version()


    def __init__(self):
        super(Arbor,self).__init__()
        self.retry_num = 3
        self.auth = {}


    def connect_all(self):
        """ Connects to all applications defined in ``local.yaml``

        The name of the connection will be the same of the `webapp` name
        """

        num = 0
        if 'webapp' in Common.LOCAL and Common.LOCAL['webapp']:
            for entry in Common.LOCAL['webapp']:
                device = Common.LOCAL['webapp'][entry]['device']
                type = Common.GLOBAL['device'][device]['type']
                if type.startswith('arbor'):
                    num += 1
                    self.connect(entry,entry)
                    BuiltIn().log("Connected to %d applications" % num)
        else:
            BuiltIn().log("WARNING: No application to connect")


    def connect(self,app,name):
        """ Opens a web browser and connects to application and assigns a
        ``name``.

        Extra information could be added to the ``webapp`` sections likes
        ``login_url``, ``browser`` or ``profile_dir``. Default values are:
        | browser     | firefox |
        | login_url   | /         |
        | profile_dir | ./config/samurai.profile |
        """
        if name in self._browsers:
            BuiltIn().log("Browser `%s` already existed. Reconnect to it" % name)
            self.close()
            # return

        login_url   = '/'
        browser     = 'firefox'
        profile_dir = None

        # collect information about the application
        app_info = Common.LOCAL['webapp'][app]
        if 'login_url' in app_info and app_info['login_url']:    
            login_url = app_info['login_url']
        if 'browser'  in app_info and app_info['browser']:    
            browser  = app_info['browser']
        if 'profile_dir' in app_info and app_info['profile_dir']:    
            ff_profile_dir  = os.getcwd() + 'config/' + app_info['profile_dir']
        if 'proxy' in app_info and app_info['proxy']:
            proxy = Proxy()
            proxy.proxy_type = ProxyType.MANUAL
            if 'http' in app_info['proxy']:
                proxy.http_proxy    = app_info['proxy']['http']
            # if 'socks' in app_info['proxy']:
            #     proxy.socks_proxy   = app_info['proxy']['socks']
            if 'ssl' in app_info['proxy']:
                proxy.ssl_proxy     = app_info['proxy']['ssl']
            if 'ftp' in app_info['proxy']:
                proxy.ftp_proxy   = app_info['proxy']['ftp']
            capabilities = webdriver.DesiredCapabilities.FIREFOX
            proxy.add_to_capabilities(capabilities)

        device = app_info['device']
        device_info = Common.GLOBAL['device'][device]
        ip = device_info['ip']
        type = device_info['type']

        template = Common.GLOBAL['access-template'][type]
        profile = template['profile']   

        # currently, only plain-text authentication is supported
        # auth = {}
        self.auth['username']    = Common.GLOBAL['auth']['plain-text'][profile]['user']
        self.auth['password']    = Common.GLOBAL['auth']['plain-text'][profile]['pass']
        url = 'https://%s/%s' %  (ip,login_url)

        ignore_dead_node = Common.get_config_value('ignore-dead-node')

        # open a browser
        try:
            self._driver.open_browser(url,browser,'_arbor_' + name,False,None,profile_dir)
            self._driver.wait_until_element_is_visible('name=username')
            # login
            self._driver.input_text('name=username', self.auth['username'])
            self._driver.input_text('name=password', self.auth['password'])
            self._driver.click_button('name=Submit')
            time.sleep(5)
    
            self._current_name = name
            self._current_app  = app
            browser_info = {}
            browser_info['capture_counter'] = 0
            browser_info['capture_format']  = 'arbor_%010d'
            browser_info['browser']         = browser
            self._browsers[name] = browser_info

            #
            self._driver.maximize_browser_window()

            BuiltIn().log("Connected to `%s` with name `%s`" % (app,name))
        except Exception as err:
            if not ignore_dead_node:
                err_msg = "ERROR: Error occured when connecting to `%s`" % (name)
                BuiltIn().log(err_msg)
                raise
            else:
                warn_msg = "WARN: Error occured when connect to `%s` but was ignored" % (name)

                BuiltIn().log(warn_msg)
                BuiltIn().log_to_console(warn_msg)
                # del Common.LOCAL['node'][name]            


    def reconnect(self):
        """ Reconnect to server if necessary
        """
        login_element_count = 0
        
        self._driver.reload_page()
        login_element_count = self._driver.get_element_count("//button[@value='Log In']")

        if login_element_count > 0: 
            BuiltIn().log("Try to reconnect to the system")
            browser_info = self._browsers[self._current_name]
            self.connect(self._current_app, self._current_name)
            # reconstruct old information
            self._browsers[self._current_name] = browser_info
            BuiltIn().log("Reconnected to the system by `%s`" % self._current_name)
        BuiltIn().log("Reload the page without any reconnection")
    

    def login(self):
        """ Logs into the Arbor application
        """
        self.switch(self._current_name) 
        self._driver.input_text('name=username', self.auth['username'])
        self._driver.input_text('name=password', self.auth['password'])
        self._driver.click_button('name=Submit')
        time.sleep(5)

    @with_reconnect 
    def logout(self):
        """ Logs-out the current application, the browser remains
        """
        self.switch(self._current_name) 
        self._driver.click_link("xpath=//a[contains(.,'(Log Out)')]")

        if self._driver.get_element_count('logout_confirm') > 0: 
            self._driver.click_button('logout_confirm')
        BuiltIn().log("Exited Arbor application")
    
    
    def switch(self,name):
        """ Switches the current browser to ``name``
        """
        self._driver.switch_browser('_arbor_' + name)
        self._current_name = name
        # a reconnect here is not good
        # it clears the previous change of any keyword
        # self.reconnect()
        BuiltIn().log("Switched the current browser to `%s`" % name)

    
    def close(self):
        """ Closes the current active browser
        """
        ignore_dead_node = Common.get_config_value('ignore-dead-node')

        try: 
            old_name = self._current_name
            self._driver.close_browser()
            del(self._browsers[old_name])
            if len(self._browsers) > 0:
                self._current_name = list(self._browsers.keys())[-1]
            else:
                self._current_name = None
        
            BuiltIn().log("Closed the browser '%s', current acttive browser is `%s`" % (old_name,self._current_name))
            return old_name
        except Exception as err:
            if not ignore_dead_node:
                err_msg = "ERROR: Error occured when connecting to `%s`" % (name)
                BuiltIn().log(err_msg)
                raise
            else:
                warn_msg = "WARN: Error occured when connect to `%s` but was ignored" % (name)

                BuiltIn().log(warn_msg)
                BuiltIn().log_to_console(warn_msg)
    
    
    def close_all(self):
        """ Closes all current opened applications
        """
        for entry in self._browsers:
            self.switch(entry)
            self._driver.close_browser()
        BuiltIn().log("Closed all Arbor applications")
    
   
    @with_reconnect 
    def show_all_mitigations(self):
        """ Shows all mitigations
        """
        
        self.switch(self._current_name)
        self._driver.mouse_over("xpath=//a[.='Mitigation']")
        self._driver.wait_until_element_is_visible("xpath=//a[contains(.,'All Mitigations')]")
        self._driver.click_link("xpath=//a[contains(.,'All Mitigations')]")
        self._driver.wait_until_element_is_visible("//div[@class='sp_page_content']")
        # time.sleep(5) 
        # self._driver.reload_page()
        # time.sleep(5) 
        BuiltIn().log("Displayed all current mitigations")


    @with_reconnect
    def show_detail_mitigation(self,search_str):
        """ Shows detail information of a mitigation by its `search_str`

        *Note*: the result could include multi mitigations
        """
        self.show_all_mitigations() 
        xpath = "//a[contains(.,'%s')]" %  search_str
        self._driver.input_text("search_string_id",search_str)
        self._driver.click_button("search_button")
        self._driver.wait_until_page_contains_element("xpath=//div[@class='sp_page_content']") 

        self._driver.wait_until_element_is_visible(xpath)
        self._driver.click_link(xpath)
        time.sleep(5)
        BuiltIn().log("Showed details of a mitigation searched by `%s`" % search_str)    


    @with_reconnect
    def show_detail_countermeasure(self,name,*method_list):
        """ Shows detail informatin about a countermeasure

        `name` is used to search the the mitigation and `method_list` is a list
        of countermeasures that are listed in Arbor Countermeasures panel

        Example:
        | ${NAME}  |   ${ID}=   |       `Show Detail First Mitigation` |
        | Arbor.`Show Detail Countermeasure` | ${NAME} | DNS Malformed |
        | Arbor.`Capture Screenshot` |
        | Sleep  | 10s |
        | Arbor.`Show Detail Countermeasure` | ${NAME} |  Zombie Detection | HTTP Malformed |  
        | Arbor.`Capture Screenshot` |
        """
        self.show_detail_mitigation(name)
        for item in method_list:
            xpath = '//table//td[(@class="borderright") and (. = "%s")]/../td[1]/a' % item
            target = self._driver.get_webelement(xpath)
            target.click()
            time.sleep(2)
        BuiltIn().log('Showed detail information for %d countermesure of mitigation `%s`' %(len(method_list),name)) 


    @with_reconnect
    def detail_first_mitigation(self):
        BuiltIn().log_to_console('WARN: This keyword is deprecated. Use `Show Detail First Mitigation` instead')
        return self.show_detail_first_mitigation()

    @with_reconnect
    def show_detail_first_mitigation(self):
        """ Shows details about the 1st mitigation on the list
    
        The keyword returns the `mitigation ID` and its name
        """
        name,id = self.show_detail_mitigation_with_order(1)
        return name,id


    @with_reconnect
    def show_detail_mitigation_with_order(self,order):
        """ Shows details about the `order`(th) mitigation in the current list

        `order` is counted from 1. 
        The keyword returns the mitigation_id and its name
        
        Example:
        | ${NAME} |  ${ID}= | Arbor.`Show Detail Mitigation With Order` | 3 |
        | Log To Console  |   ${NAME}:${ID} |
        | Arbor.`Capture Screenshot` |
        """
        self.switch(self._current_name)
        self.show_all_mitigations() 
        # ignore the header line
        xpath = '//table[1]//tr[%s]/td[%s]//a[1]' % (int(order)+1,2)
        link = self._driver.get_webelement(xpath)
        mitigation_name = link.get_attribute('innerText')
        href=link.get_attribute('href')
        mitigation_id = href.split('&')[1].split('=')[1] 
        self._driver.click_link(xpath)
        time.sleep(5)
        BuiltIn().log("Displayed detail of `%s`th mitigation in the list" % order)
        return mitigation_name,mitigation_id


    @with_reconnect
    def menu(self,order,wait='2s',capture_all=False,prefix='menu_',suffix='.png',partial_match=False):
        """ Access to Arbor menu

        Parameters
        - ``order`` is the list of top menu items separated by '/'
        - ``wait`` is the wait time after the last item is clicked
        - if ``capture_all`` is ``True`` then a screenshot is captured for each
          menu item automtically. In this case, the image file is appended by
        ``prefix`` and ``suffix``.
        - by default, the system try to match the menu item in full, when
          ``partial_match`` is ``True``, partial match is applied.

        Samples:
        | Arbor.`Menu`               |          order=Alerts/Ongoing |
        | Arbor.`Capture Screenshot` | 
        | Arbor.`Menu`               |          order=Alerts/All Alerts |
        | Arbor.`Capture Screenshot` |
        | Arbor.`Menu`               |          order=System/Status/Deployment Status |
        | Arbor.`Capture Screenshot` |
        | Arbor.`Menu`               |          order=System/Status/Signaling Status/Appliance Status | partial_match=${TRUE} |
        | Arbor.`Capture Screenshot` |
        """
        self.switch(self._current_name)
        index = 0
        items = order.split('/')
        for item in items:
            BuiltIn().log("    Access to menu item %s" % item)
            index +=1
            if partial_match:
                xpath = "xpath=//a[contains(.,'%s')]" % item
            else:
                xpath = "xpath=//a[.='%s']" % item
            self._driver.mouse_over(xpath)
            self._driver.wait_until_element_is_visible(xpath)
            if capture_all:
                capture_name='%s%s%s' % (prefix,item,suffix)
                self._driver.capture_page_screenshot(capture_name)
            if index == len(items):
                self._driver.click_link(xpath)
                time.sleep(DateTime.convert_time(wait))

