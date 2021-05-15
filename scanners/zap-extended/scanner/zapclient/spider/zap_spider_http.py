#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import collections
import logging

from zapv2 import ZAPv2, spider

from ..configuration import ZapConfiguration
from . import ZapConfigureSpider

# set up logging to file - see previous section for more details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(name)-12s %(levelname)-8s: %(message)s',
    datefmt='%Y-%m-%d %H:%M')

logging = logging.getLogger('ZapConfigureSpiderHttp')

class ZapConfigureSpiderHttp(ZapConfigureSpider):
    """This class configures a ZAP HTTP Spider in a running ZAP instance, based on a ZAP Configuration.
    
    Based on this opensource ZAP Python example:
    - https://github.com/zaproxy/zap-api-python/blob/9bab9bf1862df389a32aab15ea4a910551ba5bfc/src/examples/zap_example_api_script.py
    """

    def __init__(self, zap: ZAPv2, config: ZapConfiguration):
        """Initial constructor used for this class
        
        Parameters
        ----------
        zap : ZAPv2
            The running ZAP instance to configure.
        config : ZapConfiguration
            The configuration object containing all ZAP configs (based on the class ZapConfiguration).
        """
        self.__spider_id = -1
        
        super().__init__(zap, config)

    @property
    def get_zap_spider(self) -> spider:
        """ Returns the spider of the currently running ZAP instance."""
        return self.get_zap.spider
    
    @property
    def get_spider_id(self) -> int:
        """ Returns the spider id of the currently running ZAP instance."""
        return self.__spider_id
    
    def has_spider_id(self) -> bool:
        """ Returns a spider is currently running in the ZAP instance."""
        return self.__spider_id > 0

    def wait_until_spider_finished(self):
        """ Wait until the running ZAP HTTP Spider finished and log results."""

        if(self.has_spider_id):
            while (int(self.get_zap_spider.status(self.get_spider_id)) < 100):
                logging.info("HTTP Spider(%s) progress: %s", str(self.get_spider_id), str(self.get_zap_spider.status(self.get_spider_id)))
                time.sleep(1)
                
            logging.info("HTTP Spider(%s) completed", str(self.get_spider_id))

            # Print out a count of the number of urls
            num_urls = len(self.get_zap.core.urls())
            if num_urls == 0:
                logging.error("No URLs found - is the target URL accessible? Local services may not be accessible from the Docker container")
                raise RuntimeError('No URLs found by ZAP Spider :-( - is the target URL accessible? Local services may not be accessible from the Docker container')
            else:
                logging.info("Spider(%s) found total: %s URLs", str(self.get_spider_id), str(num_urls))
                for url in self.get_zap_spider.results(scanid=self.get_spider_id):
                    logging.info("URL: %s", url)
    
    def start_spider(self, url: str, spider_config: collections.OrderedDict):
        """ Starts a ZAP Spider with the given spiders configuration, based on the internal referenced ZAP instance.
        
        Parameters
        ----------
        spider_config: collections.OrderedDict
            The spider configuration based on ZapConfiguration.
        """
        user_id = None
        context_id = None
        context_name = None
        target = ""

        # Clear all existing/previous spider data
        logging.debug("Removing all pre existing spider scans.")     
        self.get_zap.spider.remove_all_scans()

        # Open first URL before the spider start's to crawl
        self.get_zap.core.access_url(url)

        if spider_config is not None:

            if("url" in spider_config):
                target = str(spider_config['url'])
            else:
                logging.warning("The spider configuration section has no specific 'url' target defined, trying to use scanType target instead with url: '%s'", url)
                target=url

            # Configure Spider Options if there are any
            self.configure_spider(spider_config)

            # "Context" is an optional config for spider
            if("context" in spider_config):
            
                context_name = str(spider_config['context'])
                spider_context_config = self.get_config.get_contexts.get_configuration_by_context_name(context_name)
                context_id = int(spider_context_config['id'])

                # "User" is an optional config for spider in addition to the context
                if("user" in spider_config):

                    user_name = str(spider_config['user'])
                    # search for the current ZAP Context id for the given context name
                    user_id = int(self.get_config.get_contexts.get_context_user_by_name(spider_context_config, user_name)['id'])
            else:
                logging.warning("No context 'context: XYZ' referenced within the spider config. This is ok but maybe not intended.")

            if (not context_id is None) and context_id >= 0 and (not user_id is None) and user_id >= 0:
                logging.info("Starting 'traditional' Spider(target=%s) with Context(%s) and User(%s)", target, context_id, user_id)
                result = self.get_zap_spider.scan_as_user(url=target, contextid=context_id, userid=user_id)
            else:
                logging.info("Starting 'traditional' Spider(target=%s) with Context(%s)", target, context_name)
                result = self.get_zap_spider.scan(url=target, contextname=context_name)
        else:
            logging.info("Starting 'traditional' Spider(target=%s) without any additinal configuration!", url)
            result = self.get_zap_spider.scan(url=url, contextname=None)
        
        # Check if spider is running successfully
        if (not str(result).isdigit()) or int(result) < 0:
            logging.error("Spider couldn't be started due to errors: %s", result)
            raise RuntimeError("Spider couldn't be started due to errors: %s", result)
        else:
            logging.info("HTTP Spider successfully started with id: %s", result)
            self.__spider_id = int(result)
            # Give the scanner a chance to start
            time.sleep(5)

            self.wait_until_spider_finished()
    
    def configure_spider(self, spider_config: collections.OrderedDict):
        """ Configures a ZAP HTTP Spider with the given spider configuration, based on the running ZAP instance.
        
        Parameters
        ----------
        zap_spider: spider
            The reference to the running ZAP spider to configure.
        spider_config: collections.OrderedDict
            The spider configuration based on ZapConfiguration.
        """

        logging.debug('Trying to configure the Spider')
            
        # Configure Spider (ajax or http)
        
        if "maxDuration" in spider_config and (spider_config['maxDuration'] is not None) and spider_config['maxDuration'] >= 0:
            self._check_zap_spider_result(
                result=self.get_zap_spider.set_option_max_duration(str(spider_config['maxDuration'])), 
                method="set_option_max_duration"
            )
        if "maxDepth" in spider_config and (spider_config['maxDepth'] is not None) and spider_config['maxDepth'] >= 0:
            self._check_zap_spider_result(
                result=self.get_zap_spider.set_option_max_depth(str(spider_config['maxDepth'])), 
                method="set_option_max_depth"
            )
        if "maxChildren" in spider_config and (spider_config['maxChildren'] is not None) and spider_config['maxChildren'] >= 0:
            self._check_zap_spider_result(
                result=self.get_zap_spider.set_option_max_children(str(spider_config['maxChildren'])), 
                method="set_option_max_children"
            )
        if "maxParseSizeBytes" in spider_config and (spider_config['maxParseSizeBytes'] is not None) and spider_config['maxParseSizeBytes'] >= 0:
            self._check_zap_spider_result(
                result=self.get_zap_spider.set_option_max_parse_size_bytes(str(spider_config['maxParseSizeBytes'])), 
                method="set_option_max_parse_size_bytes"
            )
        if "acceptCookies" in spider_config and (spider_config['acceptCookies'] is not None) :
            self._check_zap_spider_result(
                result=self.get_zap_spider.set_option_accept_cookies(str(spider_config['acceptCookies'])), 
                method="set_option_accept_cookies"
            )
        if "handleODataParametersVisited" in spider_config and (spider_config['handleODataParametersVisited'] is not None) :
            self._check_zap_spider_result(
                result=self.get_zap_spider.set_option_handle_o_data_parameters_visited(str(spider_config['handleODataParametersVisited'])), 
                method="set_option_handle_o_data_parameters_visited"
            )
        if "handleParameters" in spider_config and (spider_config['handleParameters'] is not None) :
            self._check_zap_spider_result(
                result=self.get_zap_spider.set_option_handle_parameters(str(spider_config['handleParameters'])), 
                method="set_option_handle_parameters"
            )
        
        if "parseComments" in spider_config and (spider_config['parseComments'] is not None) :
            self._check_zap_spider_result(
                result=self.get_zap_spider.set_option_parse_comments(str(spider_config['parseComments'])), 
                method="set_option_parse_comments"
            )
        if "parseGit" in spider_config and (spider_config['parseGit'] is not None) :
            self._check_zap_spider_result(
                result=self.get_zap_spider.set_option_parse_git(str(spider_config['parseGit'])), 
                method="set_option_parse_git"
            )
        if "parseRobotsTxt" in spider_config and (spider_config['parseRobotsTxt'] is not None) :
            self._check_zap_spider_result(
                result=self.get_zap_spider.set_option_parse_robots_txt(str(spider_config['parseRobotsTxt'])), 
                method="set_option_parse_robots_txt"
            )
        if "parseSitemapXml" in spider_config and (spider_config['parseSitemapXml'] is not None) :
            self._check_zap_spider_result(
                result=self.get_zap_spider.set_option_parse_sitemap_xml(str(spider_config['parseSitemapXml'])), 
                method="set_option_parse_sitemap_xml"
            )
        if "parseSVNEntries" in spider_config and (spider_config['parseSVNEntries'] is not None) :
            self._check_zap_spider_result(
                result=self.get_zap_spider.set_option_parse_svn_entries(str(spider_config['parseSVNEntries'])), 
                method="set_option_parse_svn_entries"
            )
        if "postForm" in spider_config and (spider_config['postForm'] is not None) :
            self._check_zap_spider_result(
                result=self.get_zap_spider.set_option_post_form(str(spider_config['postForm'])), 
                method="set_option_post_form"
            )
        if "processForm" in spider_config and (spider_config['processForm'] is not None) :
            self._check_zap_spider_result(
                result=self.get_zap_spider.set_option_process_form(str(spider_config['processForm'])), 
                method="set_option_process_form"
            )
        
        if "requestWaitTime" in spider_config and (spider_config['requestWaitTime'] is not None) :
            self._check_zap_spider_result(
                result=self.get_zap_spider.set_option_request_wait_time(str(spider_config['requestWaitTime'])), 
                method="set_option_request_wait_time"
            )
        if "sendRefererHeader" in spider_config and (spider_config['sendRefererHeader'] is not None) :
            self._check_zap_spider_result(
                result=self.get_zap_spider.set_option_send_referer_header(str(spider_config['sendRefererHeader'])), 
                method="set_option_send_referer_header"
            )
        if "threadCount" in spider_config and (spider_config['threadCount'] is not None) and spider_config['threadCount'] >= 0:
            self._check_zap_spider_result(
                result=self.get_zap_spider.set_option_thread_count(str(spider_config['threadCount'])), 
                method="set_option_thread_count"
            )
        if "userAgent" in spider_config and (spider_config['userAgent'] is not None) and len(spider_config['userAgent']) > 0:
            self._check_zap_spider_result(
                result=self.get_zap_spider.set_option_user_agent(string=str(spider_config['userAgent'])), 
                method="set_option_user_agent"
            )
