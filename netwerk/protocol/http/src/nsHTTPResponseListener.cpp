/* -*- Mode: C++; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 4 -*-
 *
 * The contents of this file are subject to the Netscape Public License
 * Version 1.0 (the "NPL"); you may not use this file except in
 * compliance with the NPL.  You may obtain a copy of the NPL at
 * http://www.mozilla.org/NPL/
 *
 * Software distributed under the NPL is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the NPL
 * for the specific language governing rights and limitations under the
 * NPL.
 *
 * The Initial Developer of this code under the NPL is Netscape
 * Communications Corporation.  Portions created by Netscape are
 * Copyright (C) 1998 Netscape Communications Corporation.  All Rights
 * Reserved.
 */

#include "nspr.h"
#include "nsIStreamListener.h"
#include "nsHTTPResponseListener.h"
#include "nsIChannel.h"
#include "nsIBufferInputStream.h"
#include "nsHTTPChannel.h"
#include "nsHTTPResponse.h"
#include "nsIHttpEventSink.h"
#include "nsCRT.h"

#include "nsHTTPAtoms.h"
#include "nsIHttpNotify.h"
#include "nsINetModRegEntry.h"
#include "nsIServiceManager.h"
#include "nsINetModuleMgr.h"
#include "nsIBuffer.h"

#include "nsIIOService.h"
static NS_DEFINE_CID(kIOServiceCID, NS_IOSERVICE_CID);

#if defined(PR_LOGGING)
extern PRLogModuleInfo* gHTTPLog;
#endif /* PR_LOGGING */

//
// This specifies the maximum allowable size for a server Status-Line
// or Response-Header.
//
static const int kMAX_HEADER_SIZE = 60000;


nsHTTPResponseListener::nsHTTPResponseListener(nsHTTPChannel* aConnection): 
    m_bFirstLineParsed(PR_FALSE),
    m_pResponse(nsnull),
    m_pConsumer(nsnull),
    m_ReadLength(0),
    m_bHeadersDone(PR_FALSE),
    m_HeaderBuffer(eOneByte),
    m_ResponseContext(nsnull),
    m_Channel(nsnull)
{
    NS_INIT_REFCNT();

    NS_ASSERTION(aConnection, "HTTPChannel is null.");
    m_pConnection = aConnection;
    NS_IF_ADDREF(m_pConnection);

    PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
           ("Creating nsHTTPResponseListener [this=%x].\n", this));

}

nsHTTPResponseListener::~nsHTTPResponseListener()
{
    PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
           ("Deleting nsHTTPResponseListener [this=%x].\n", this));

    NS_IF_RELEASE(m_pConnection);
    NS_IF_RELEASE(m_pResponse);
    NS_IF_RELEASE(m_pConsumer);
}

NS_IMPL_ISUPPORTS(nsHTTPResponseListener,nsCOMTypeInfo<nsIStreamListener>::GetIID());

static NS_DEFINE_CID(kNetModuleMgrCID, NS_NETMODULEMGR_CID);

NS_IMETHODIMP
nsHTTPResponseListener::OnDataAvailable(nsIChannel* channel,
                                        nsISupports* context,
                                        nsIInputStream *i_pStream, 
                                        PRUint32 i_SourceOffset,
                                        PRUint32 i_Length)
{
    nsresult rv = NS_OK;
    PRUint32 actualBytesRead;
    NS_ASSERTION(i_pStream, "No stream supplied by the transport!");
	nsCOMPtr<nsIBufferInputStream> bufferInStream = do_QueryInterface(i_pStream);

    PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
           ("nsHTTPResponseListener::OnDataAvailable [this=%x].\n"
            "\tstream=%x. \toffset=%d. \tlength=%d.\n",
            this, i_pStream, i_SourceOffset, i_Length));

    if (!m_pResponse)
    {
        // why do I need the connection in the constructor... get rid.. TODO
        m_pResponse = new nsHTTPResponse (bufferInStream);
        if (!m_pResponse) {
            NS_ERROR("Failed to create the response object!");
            return NS_ERROR_OUT_OF_MEMORY;
        }
        NS_ADDREF(m_pResponse);
        m_pConnection->SetResponse(m_pResponse);
    }
    //
    // Parse the status line and the response headers from the server
    //
    if (!m_bHeadersDone) {
        nsCOMPtr<nsIBuffer> pBuffer;

        rv = bufferInStream->GetBuffer(getter_AddRefs(pBuffer));
        if (NS_FAILED(rv)) return rv;
        //
        // Parse the status line from the server.  This is always the 
        // first line of the response...
        //
        if (!m_bFirstLineParsed) {
            rv = ParseStatusLine(pBuffer, i_Length, &actualBytesRead);
            i_Length -= actualBytesRead;
        }

        PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
               ("\tOnDataAvailable [this=%x]. Parsing Headers\n", this));
        //
        // Parse the response headers as long as there is more data and
        // the headers are not done...
        //
        while (NS_SUCCEEDED(rv) && i_Length && !m_bHeadersDone) {
            rv = ParseHTTPHeader(pBuffer, i_Length, &actualBytesRead);
			NS_ASSERTION(i_Length - actualBytesRead <= i_Length, "wrap around");
            i_Length -= actualBytesRead;
        }

        if (NS_FAILED(rv)) return rv;
        //
        // All the headers have been read.  Check the status code of the 
        // response to see if any special action should be taken.
        //
        if (m_bHeadersDone) {
            rv = FinishedResponseHeaders();
        }
    }

    if (NS_SUCCEEDED(rv) && m_pConsumer) {
        if (i_Length) {
            PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
                   ("\tOnDataAvailable [this=%x]. Calling consumer "
                    "OnDataAvailable.\tlength:%d\n", this, i_Length));

            rv = m_pConsumer->OnDataAvailable(m_pConnection, m_ResponseContext, i_pStream, 0, 
                                              i_Length);
        }
    } 

    return rv;
}


NS_IMETHODIMP
nsHTTPResponseListener::OnStartRequest(nsIChannel* channel, nsISupports* i_pContext)
{
    nsresult rv;

    PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
           ("nsHTTPResponseListener::OnStartRequest [this=%x].\n", this));

    // Initialize header varaibles...  
    m_bHeadersDone     = PR_FALSE;
    m_bFirstLineParsed = PR_FALSE;

    // Cache the nsIStreamListener and ISupports context of the consumer...
    rv = m_pConnection->GetResponseDataListener(&m_pConsumer);
    if (NS_SUCCEEDED(rv)) {
        rv = m_pConnection->GetResponseContext(getter_AddRefs(m_ResponseContext));
    }

    return rv;
}

NS_IMETHODIMP
nsHTTPResponseListener::OnStopRequest(nsIChannel* channel,
                                      nsISupports* i_pContext,
                                      nsresult i_Status,
                                      const PRUnichar* i_pMsg)
{
    nsresult rv = NS_OK;

    PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
           ("nsHTTPResponseListener::OnStopRequest [this=%x].\n", this));

    if (NS_SUCCEEDED(rv) && !m_bHeadersDone) {
        //
        // Oh great!!  The server has closed the connection without sending 
        // an entity.  Assume that it has sent all the response headers and
        // process them - in case the status indicates that some action should
        // be taken (ie. redirect).
        //
        // Ignore the return code, since the request is being completed...
        //
        m_bHeadersDone = PR_TRUE;
        if (m_pResponse) {
            (void)FinishedResponseHeaders();
        }
    }

    // Pass the notification out to the consumer...
    if (m_pConsumer) {
        rv = m_pConsumer->OnStopRequest(m_pConnection, m_ResponseContext, i_Status, i_pMsg);
    }

    // Notify the HTTPChannel that the response has completed...
    NS_ASSERTION(m_pConnection, "HTTPChannel is null.");
    if (m_pConnection) {
        m_pConnection->ResponseCompleted(channel);
    }

    // The Consumer is no longer needed...
    NS_IF_RELEASE(m_pConsumer);

    // The HTTPChannel is no longer needed...
    NS_IF_RELEASE(m_pConnection);

    // The Response Context is no longer needed...
    m_ResponseContext = nsnull;

    return rv;
}

nsresult nsHTTPResponseListener::FireOnHeadersAvailable()
{
    nsresult rv;
    NS_ASSERTION(m_bHeadersDone, "Headers have not been received!");

    if (m_bHeadersDone) 
    {

        // Notify the event sink that response headers are available...
        nsCOMPtr<nsIHTTPEventSink> sink;
        m_pConnection->GetEventSink(getter_AddRefs(sink));
        if (sink) {
            sink->OnHeadersAvailable(m_pConnection);
        }
        // Check for any modules that want to receive headers once they've arrived.
        NS_WITH_SERVICE(nsINetModuleMgr, pNetModuleMgr, kNetModuleMgrCID, &rv);
        if (NS_FAILED(rv)) return rv;

        nsCOMPtr<nsISimpleEnumerator> pModules;
        rv = pNetModuleMgr->EnumerateModules(NS_NETWORK_MODULE_MANAGER_HTTP_REQUEST_PROGID, getter_AddRefs(pModules));
        if (NS_FAILED(rv)) return rv;

        // Go through the external modules and notify each one.
        nsISupports *supEntry;
        rv = pModules->GetNext(&supEntry);
        while (NS_SUCCEEDED(rv)) 
        {
            nsCOMPtr<nsINetModRegEntry> entry = do_QueryInterface(supEntry, &rv);
            if (NS_FAILED(rv)) 
                return rv;

            nsCOMPtr<nsINetNotify> syncNotifier;
            entry->GetSyncProxy(getter_AddRefs(syncNotifier));
            nsCOMPtr<nsIHTTPNotify> pNotify = do_QueryInterface(syncNotifier, &rv);

            if (NS_SUCCEEDED(rv)) 
            {
                // send off the notification, and block.
                // make the nsIHTTPNotify api call
                pNotify->AsyncExamineResponse(m_pConnection);
                // we could do something with the return code from the external
                // module, but what????            
            }
            rv = pModules->GetNext(&supEntry); // go around again
        }
    } 
    else 
    {
        rv = NS_ERROR_FAILURE;
    }

    return rv;
}

NS_METHOD
nsWriteToString(void* closure,
                const char* fromRawSegment,
                PRUint32 offset,
                PRUint32 count,
                PRUint32 *writeCount)
{
  nsString *str = (nsString*)closure;

  str->Append(fromRawSegment, count);
  *writeCount = count;
  
  return NS_OK;
}


nsresult nsHTTPResponseListener::ParseStatusLine(nsIBuffer* aBuffer, 
                                                 PRUint32 aLength,
                                                 PRUint32 *aBytesRead)
{
  nsresult rv = NS_OK;

  PRBool bFoundString = PR_FALSE;
  PRUint32 offsetOfEnd, totalBytesToRead, actualBytesRead;

  PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
         ("nsHTTPResponseListener::ParseStatusLine [this=%x].\taLength=%d\n", 
          this, aLength));

  *aBytesRead = 0;

  if (kMAX_HEADER_SIZE < m_HeaderBuffer.Length()) {
    // This server is yanking our chain...
    return NS_ERROR_FAILURE;
  }

  // Look for the LF which ends the Status-Line.
  rv = aBuffer->Search("\n", PR_FALSE, &bFoundString, &offsetOfEnd);
  if (NS_FAILED(rv)) return rv;

  if (!bFoundString) {
    //
    // This is a partial header...  Read the entire buffer and wait for
    // more data...
    //
    totalBytesToRead = aLength;
  } else {
    // Do not forget to include the LF character in the read...
    totalBytesToRead = offsetOfEnd+1;
  }

  rv = aBuffer->ReadSegments(nsWriteToString, 
                             (void*)&m_HeaderBuffer, 
                             totalBytesToRead, 
                             &actualBytesRead);
  if (NS_FAILED(rv)) return rv;

  *aBytesRead += actualBytesRead;

  // Wait for more data to arrive before processing the header...
  if (!bFoundString) return NS_OK;

  PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
         ("\tParseStatusLine [this=%x].\tGot Status-Line:%s\n"
         , this, m_HeaderBuffer.GetBuffer()));

  //
  // Replace all LWS with single SP characters.  Also remove the CRLF
  // characters...
  //
  m_HeaderBuffer.CompressSet(" \t", ' ');
  m_HeaderBuffer.StripChars("\r\n");

  //
  // The Status Line has the following: format:
  //    HTTP-Version SP Status-Code SP Reason-Phrase CRLF
  //

  const char *token;
  nsAutoString str(eOneByte);
  PRInt32 offset, error;

  //
  // Parse the HTTP-Version:: "HTTP" "/" 1*DIGIT "." 1*DIGIT
  //

  offset = m_HeaderBuffer.Find(' ');
  (void) m_HeaderBuffer.Left(str, offset);
  if (!str.Length()) {
    // The status line is bogus...
    return NS_ERROR_FAILURE;
  }
  token = str.GetBuffer();
  m_pResponse->SetServerVersion(token);

  PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
         ("\tParseStatusLine [this=%x].\tHTTP-Version: %s\n",
          this, token));

  m_HeaderBuffer.Cut(0, offset+1);

  //
  // Parse the Status-Code:: 3DIGIT
  //
  PRInt32 statusCode;

  offset = m_HeaderBuffer.Find(' ');
  (void) m_HeaderBuffer.Left(str, offset);
  if (3 != str.Length()) {
    // The status line is bogus...
    return NS_ERROR_FAILURE;
  }

  statusCode = str.ToInteger(&error);
  if (NS_FAILED(error)) return NS_ERROR_FAILURE;

  m_pResponse->SetStatus(statusCode);
  
  PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
         ("\tParseStatusLine [this=%x].\tStatus-Code: %d\n",
          this, statusCode));

  m_HeaderBuffer.Cut(0, offset+1);

  //
  // Parse the Reason-Phrase:: *<TEXT excluding CR,LF>
  //
  token = m_HeaderBuffer.GetBuffer();
  m_pResponse->SetStatusString(token);

  PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
         ("\tParseStatusLine [this=%x].\tReason-Phrase: %s\n",
          this, token));

  m_HeaderBuffer.Truncate();
  m_bFirstLineParsed = PR_TRUE;
  
  return rv;
}



nsresult nsHTTPResponseListener::ParseHTTPHeader(nsIBuffer* aBuffer,
                                                 PRUint32 aLength,
                                                 PRUint32 *aBytesRead)
{
  nsresult rv = NS_OK;

  const char *buf;
  PRBool bFoundString;
  PRUint32 offsetOfEnd, totalBytesToRead, actualBytesRead;

  *aBytesRead = 0;

  if (kMAX_HEADER_SIZE < m_HeaderBuffer.Length()) {
    // This server is yanking our chain...
    return NS_ERROR_FAILURE;
  }

  //
  // Read the header from the input buffer...  A header is terminated by 
  // a CRLF.  Header values may be extended over multiple lines by preceeding
  // each extran line with LWS...
  //
  do {
    //
    // If last character in the header string is a LF, then the header 
    // may be complete...
    //
    if (m_HeaderBuffer.Last() == '\n' ) {
      rv = aBuffer->GetReadSegment(0, &buf, &actualBytesRead);
      // Need to wait for more data to see if the header is complete.
      if (0 == actualBytesRead) {
        return NS_OK;
      }

      // Not LWS - The header is complete...
      if ((*buf != ' ') && (*buf != '\t')) {
        break;
      }
    }

    // Look for the next LF in the buffer...
    rv = aBuffer->Search("\n", PR_FALSE, &bFoundString, &offsetOfEnd);
    if (NS_FAILED(rv)) return rv;

    if (!bFoundString) {
      //
      // The buffer contains a partial header.  Read the entire buffer 
      // and wait for more data...
      //
      totalBytesToRead = aLength;
    } else {
    // Do not forget to include the LF character in the read...
      totalBytesToRead = offsetOfEnd+1;
    }

    // Append the buffer into the header string...
    rv = aBuffer->ReadSegments(nsWriteToString, 
                               (void*)&m_HeaderBuffer, 
                               totalBytesToRead, 
                               &actualBytesRead);
    if (NS_FAILED(rv)) return rv;

    *aBytesRead += actualBytesRead;

    // Partial header - wait for more data to arrive...
    if (!bFoundString) return NS_OK;

  } while (PR_TRUE);

  PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
         ("\tParseHTTPHeader [this=%x].\tGot header string:%s\n",
          this, m_HeaderBuffer.GetBuffer()));

  //
  // Replace all LWS with single SP characters.  And remove all of the CRLF
  // characters...
  //
  m_HeaderBuffer.CompressSet(" \t", ' ');
  m_HeaderBuffer.StripChars("\r\n");

  if (!m_HeaderBuffer.Length()) {
    m_bHeadersDone = PR_TRUE;
    return NS_OK;
  }

  //
  // Extract the key field - everything up to the ':'
  // The header name is case-insensitive...
  //
  PRInt32 colonOffset;
  nsAutoString headerKey(eOneByte);
  nsCOMPtr<nsIAtom> headerAtom;

  colonOffset = m_HeaderBuffer.Find(':');
  if (-1 == colonOffset) {
    //
    // The header is malformed... Just clear it.
    //
    m_HeaderBuffer.Truncate();
    return NS_ERROR_FAILURE;
  }
  (void) m_HeaderBuffer.Left(headerKey, colonOffset);
  headerKey.ToLowerCase();
  //
  // Extract the value field - everything past the ':'
  // Trim any leading or trailing whitespace...
  //
  m_HeaderBuffer.Cut(0, colonOffset+1);
  m_HeaderBuffer.Trim(" ");

  headerAtom = NS_NewAtom(headerKey.GetBuffer());
  if (headerAtom) {
    rv = ProcessHeader(headerAtom, m_HeaderBuffer);
  } else {
    rv = NS_ERROR_OUT_OF_MEMORY;
  }

  m_HeaderBuffer.Truncate();

  return rv;
}


nsresult nsHTTPResponseListener::FinishedResponseHeaders(void)
{
  nsresult rv = NS_OK;

  PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
         ("nsHTTPResponseListener::FinishedResponseHeaders [this=%x].\n",
          this));
  //
  // Check the status code to see if any special processing is necessary.
  //
  // If a redirect (ie. 30x) occurs, the m_pConsumer is released and a new
  // request is issued...
  //
  rv = ProcessStatusCode();

  //
  // Fire the OnStartRequest notification - now that user data is available
  //
  if (NS_SUCCEEDED(rv) && m_pConsumer) {
    rv = m_pConsumer->OnStartRequest(m_pConnection, m_ResponseContext);
    if (NS_FAILED(rv)) return rv;

    // Notify the consumer that headers are available...
    FireOnHeadersAvailable();
  } 

  return rv;
}


nsresult nsHTTPResponseListener::ProcessHeader(nsIAtom* aHeader, 
                                               nsString& aValue)
{
  nsresult rv;

  if (nsHTTPAtoms::Content_Type == aHeader) {
    nsAutoString buffer(eOneByte);
    PRInt32 semicolon;

    //
    // Set the content-type in the HTTPChannel...
    //
    semicolon = aValue.Find(';');
    if (-1 != semicolon) {
      aValue.Left(buffer, semicolon);
      m_pConnection->SetContentType(buffer.GetBuffer());
    } else {
      m_pConnection->SetContentType(aValue.GetBuffer());
    }
  }

  //
  // Set the response header...
  //
  rv = m_pResponse->SetHeader(aHeader, aValue.GetBuffer());

  return rv;
}


nsresult nsHTTPResponseListener::ProcessStatusCode(void)
{
  nsresult rv = NS_OK;
  PRUint32 statusCode, statusClass;

  statusCode = 0;
  rv = m_pResponse->GetStatus(&statusCode);
  statusClass = statusCode / 100;


  switch (statusClass) {
    //
    // Informational: 1xx
    //
    case 1:
      PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
             ("ProcessStatusCode [this=%x].\tStatus - Informational: %d.\n",
              this, statusCode));
      break;

    //
    // Successful: 2xx
    //
    case 2:
      PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
             ("ProcessStatusCode [this=%x].\tStatus - Successful: %d.\n",
              this, statusCode));
      break;

    //
    // Redirection: 3xx
    //
    case 3:
      PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
             ("ProcessStatusCode [this=%x].\tStatus - Redirection: %d.\n",
              this, statusCode));
      rv = ProcessRedirection(statusCode);
      break;

    //
    // Client Error: 4xx
    //
    case 4:
      PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
             ("ProcessStatusCode [this=%x].\tStatus - Client Error: %d.\n",
              this, statusCode));
      break;

    //
    // Server Error: 5xx
    //
    case 5:
      PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
             ("ProcessStatusCode [this=%x].\tStatus - Server Error: %d.\n",
              this, statusCode));
      break;

    //
    // Unknown Status Code catagory...
    //
    default:
      PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
             ("ProcessStatusCode [this=%x].\tStatus - Unknown Status Code catagory: %d.\n",
              this, statusCode));
      break;
  }

  return rv;
}



nsresult nsHTTPResponseListener::ProcessRedirection(PRInt32 aStatusCode)
{
  nsresult rv = NS_OK;
  char *location;

  location = nsnull;
  m_pResponse->GetHeader(nsHTTPAtoms::Location, &location);

  if ((301 == aStatusCode) || (302 == aStatusCode)) {
    if (location) {
      nsCOMPtr<nsIURI> baseURL, newURL;

      //
      // Create a new URI using the Location header and the current URL 
      // as a base ...
      //
#if 0
      // Expanded inline to avoid linking with neckoutils....  (temporary)
      rv = NS_NewURI(getter_AddRefs(newURL), location, baseURL);
#else
      NS_WITH_SERVICE(nsIIOService, serv, kIOServiceCID, &rv);
      if (NS_FAILED(rv)) return rv;
    
      m_pConnection->GetURI(getter_AddRefs(baseURL));
      rv = serv->NewURI(location, baseURL, getter_AddRefs(newURL));
#endif
            
      if (NS_SUCCEEDED(rv)) {

#if defined(PR_LOGGING)
        char *newURLSpec;

        newURLSpec = nsnull;
        newURL->GetSpec(&newURLSpec);
        PR_LOG(gHTTPLog, PR_LOG_DEBUG, 
               ("ProcessRedirect [this=%x].\tRedirecting to: %s.\n",
                this, newURLSpec));
#endif /* PR_LOGGING */
#if 0
      // Expanded inline to avoid linking with neckoutils....  (temporary)
        rv = NS_OpenURI(m_pConsumer, m_ResponseContext, newURL);
#else
        nsIChannel* channel;
        rv = serv->NewChannelFromURI("load", newURL, nsnull, &channel);
        if (NS_SUCCEEDED(rv)) {
            nsCOMPtr<nsILoadGroup> group;
            rv = m_pConnection->GetLoadGroup(getter_AddRefs(group));
            if (group) {
                // Add the new channel first. That way we don't run the risk
                // of emptying the group and firing off the OnEndDocumentLoad
                // notification.
                (void)group->AddChannel(channel, m_ResponseContext);
                (void)group->RemoveChannel(m_pConnection, m_ResponseContext,
                                           aStatusCode, nsnull);        // XXX error message
            }
            rv = channel->AsyncRead(0, -1, m_ResponseContext, m_pConsumer);
            NS_RELEASE(channel);
        }
#endif
        if (NS_SUCCEEDED(rv)) {
          nsCOMPtr<nsIHTTPEventSink> sink;
          //
          // Fire the OnRedirect(...) notification.
          //
          m_pConnection->GetEventSink(getter_AddRefs(sink));
          if (sink) {
            sink->OnRedirect(m_pConnection, newURL);
          }

          //
          // Disconnect the consumer from this response listener...  This allows
          // the entity that follows to be discarded without notifying the 
          // consumer...
          //
          NS_RELEASE(m_pConsumer);
          m_ResponseContext = nsnull;
        }
      }
      nsCRT::free(location);
    }
  }
  return rv;
}
