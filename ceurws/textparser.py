'''
Created on 2022-08-15

@author: wf
'''
# import logging

class Textparser():
    '''
    general text parser
    '''
    def __init__(self,debug:bool):
        '''
        Constructor
        
        Args:
            debug(bool): if TRUE switch debugging on
        '''
        self.debug=debug
    
    
    @classmethod
    def sanitize(cls,text,replaceList=[]):
        if text is not None:
            sanitizeChars="\n\t\r., "
            text=text.strip(sanitizeChars)
            text=text.replace("\n"," ")
            text=text.replace("\r","")
            for replace in replaceList:
                text=text.replace(replace,"")
            # compress multiple spaces
            text=' '.join(text.split())
        return text
    
    def log(self,msg:str):
        '''
        log the given message if debug is on
        
        Args:
            msg(str): the message to log
        '''
        if self.debug:
            print(msg)
            
    def hasValue(self,d,key):
        '''
        check that the given attribute in the given dict is available and not none
        
        Args:
            d(dict): the dict
            key(str): the key
            
        Returns:
            True: if a not None Value is available
        '''
        result=key in d and d[key] is not None
        return result
            
            
    def getMatch(self,pattern,text,groupNo:int=1):
        '''
        get the match for the given regular expression for the given text returning the given group number
        
        Args:
            regexp(str): the regular expression to check
            text(str): the text to check
            groupNo(int): the number of the regular expression group to return
            
        Returns:
            str: the matching result or None if no match was found
        '''
        matchResult=pattern.match(text)
        if matchResult:
            return matchResult.group(groupNo)
        else:
            return None