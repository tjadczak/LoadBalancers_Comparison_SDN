#include "sock.h"
#include <stdio.h>
#include <stdarg.h>

void tracef(const char* str, ...)
{
    va_list args;
    va_start(args, str);
    //vprintf(str, args);
    va_end(args);
};

#ifdef WIN32

#pragma comment( lib, "wsock32" )

typedef int socklen_t;

class dummy
{
public:
    dummy();
    ~dummy();
};

static dummy theDummy;

dummy::dummy()
{
    tracef("WSAStartup\n");
    WORD wVersionRequested;
    WSADATA wsaData;
    int err; 

    wVersionRequested = MAKEWORD( 1, 1 ); 
    err = WSAStartup( wVersionRequested, &wsaData );
    if ( err != 0 )
    {
        /* Tell the user that we could not find a usable */
        /* WinSock DLL.                                  */
        return;
    } 

    /* Confirm that the WinSock DLL supports 1.1.*/
    /* Note that if the DLL supports versions greater    */
    /* than 1.1 in addition to 1.1, it will still return */
    /* 1.1 in wVersion since that is the version we      */
    /* requested.                                        */ 
    if ( LOBYTE( wsaData.wVersion ) != 1 ||
        HIBYTE( wsaData.wVersion ) != 1 )
    {
        /* Tell the user that we could not find a usable */
        /* WinSock DLL.                                  */
        WSACleanup( );
        return;
    }

    /* The WinSock DLL is acceptable. Proceed. */
    return;
}

dummy::~dummy()
{
    tracef("WSACleanup\n");
    WSACleanup();
}

int getSocketError()
{
    return WSAGetLastError();
}

int setNonBlocking(SOCKET sock)
{
    unsigned long arg = 1;
    return ioctlsocket(sock, FIONBIO, &arg);
}

#else // WIN32

#include <sys/ioctl.h>
#include <netdb.h>
#include <string.h>
#include <fcntl.h>
#include <errno.h>

#define INVALID_SOCKET (-1)

typedef struct hostent HOSTENT;
typedef struct sockaddr SOCKADDR;

int getSocketError()
{
    return errno;
}

int closesocket(SOCKET s)
{
    return close(s);
}

int setNonBlocking(SOCKET sock)
{
    int status = 1;
    if((status = fcntl(sock, F_GETFL, 0)) != -1)
    {
	status |= O_NONBLOCK;
	status = fcntl(sock, F_SETFL, status);
    }
    return status;
}

#endif // WIN32


int get_address(const char* host, int port, SOCKADDR_IN* pAdr)
{
    // first try name as ip addr
    pAdr->sin_addr.s_addr = inet_addr(host);
    if(pAdr->sin_addr.s_addr == INADDR_NONE)
    {
        // now try name lookup
        HOSTENT* phe;
        phe = gethostbyname(host);
        if(phe == NULL)
            return -1;

        memcpy(&pAdr->sin_addr.s_addr, phe->h_addr, sizeof(pAdr->sin_addr.s_addr));
    }

    pAdr->sin_family = AF_INET;
    pAdr->sin_port = htons(port);
    memset(pAdr->sin_zero, 0, sizeof(pAdr->sin_zero));

    return 0;
}

/* ----------------------------------------------
 * CTcpSock implementation
 * ----------------------------------------------
 */

CTcpSock::CTcpSock(void)
{
    m_state = start;
    m_context = NULL;
    m_cbConnectOk = NULL;
    m_cbSendOk = NULL;
    m_cbReadLineOk = NULL;
    m_cbRecvBufOk = NULL;
    m_intStatus = noEvent;
    m_eof = 0;
}

CTcpSock::~CTcpSock(void)
{
    close();
}

int CTcpSock::create(void)
{
    tracef("creating socket ... ");
    m_sock = ::socket(AF_INET, SOCK_STREAM, 0);
    if(m_sock != INVALID_SOCKET)
    {
	setNonBlocking(m_sock);
        // TODO: check for failure to set nonblocking socket
        m_state = created;
        tracef("OK, fd=0x%08x\n", m_sock);
        return 0;
    }
    else
    {
        tracef("FAILED\n");
        return -1;
    }
}

int CTcpSock::close(void)
{
    int res = 0;
    if(m_state != closed &&
        m_state != start)
    {
        tracef("closing socket ... ");
        res = ::closesocket(m_sock);
        if(res == 0)
        {
            m_state = closed;
            tracef("OK\n");
        }
        else
        {
            tracef("FAILED [%d]\n", getSocketError());
        }
    }
    return res;
}

int CTcpSock::connect(SOCKADDR_IN* name)
{
    tracef("connecting to %s\n", inet_ntoa(name->sin_addr));
    int res = 0;
    if(m_state == created)
    {
        res = ::connect(m_sock, (SOCKADDR*) name, sizeof(SOCKADDR_IN));
        m_state = connecting;
    }
    return res;
}

int CTcpSock::send(const char* buf, int len)
{
    tracef("sending %d bytes\n", len);
    tracef(" %s\n", buf);
    int res = 0;
    if(m_state == ready)
    {
        res = ::send(m_sock, buf, len, 0);
        m_sent = res;
        m_wlen = len;
        m_wbuf = buf;
	if(res < 0)
	{
	    tracef("send error: %d\n", getSocketError());
	    m_sent = 0;
	}
        if(res < len)
        {
            m_state = sending;
        }
        else
        {
            tracef("send DONE OK\n");
            m_state = ready;
            m_intStatus = sendOk;
        }
    }
    return res;
}

int CTcpSock::sendString(const char* str)
{
    return send(str, strlen(str));
}

void CTcpSock::recvBufLoop(void)
{
    int res = 0;
    m_state = recievingBuf;
    while(1)
    {
        m_eof = 0;
        int done = 0;
        res = ::recv(m_sock, &m_rbuf[m_read], m_rlen - m_read, 0);
        if(res < 0)
            break;
        if(res == 0)
        {
            m_eof = 1;
            done = 1;
        }
        m_read += res;
        if(m_read == m_rlen)
            done = 1;
        if(done)
        {
            m_state = ready;
            m_intStatus = recvBufOk;
            break;
        }
    }
}

int CTcpSock::recvBuf(char* buf, int len)
{
    tracef("Receiving buffer ...\n");
    int res = 0;
    if(m_state == ready)
    {
        m_read = 0;
        m_rlen = len;
        m_rbuf = buf;
        recvBufLoop();
    }
    return res;
}

void CTcpSock::readLineLoop(void)
{
    int res = 0;
    m_state = readingLine;
    while(1)
    {
        m_eof = 0;
        int done = 0;
        res = ::recv(m_sock, &m_rbuf[m_read], 1, 0);
        if(res < 0)
            break;
        if(res == 0)
        {
            m_eof = 1;
            done = 1;
        }
        if(m_rbuf[m_read] == 10)
        {
            done = 1;
        }
        else
        {
            if(m_rbuf[m_read] != 13)
                m_read += res;
        }
        if(m_read >= m_rlen - 1)
            done = 1;
        if(done)
        {
            m_rbuf[m_read] = 0;
            m_state = ready;
            m_intStatus = readLineOk;
            break;
        }
    }
}

int CTcpSock::readLine(char* buf, int max_len)
{
    tracef("reading line ... \n");
    int res = 0;
    if(m_state == ready)
    {
        m_read = 0;
        m_rlen = max_len;
        m_rbuf = buf;
        readLineLoop();
    }

    return res;
}

int CTcpSock::setFdSets(fd_set* rfds, fd_set* wfds, fd_set* efds)
{
    FD_CLR(m_sock, rfds);
    FD_CLR(m_sock, wfds);
    FD_SET(m_sock, efds);

    switch(m_state)
    {
    case connecting:
        FD_SET(m_sock, wfds);
        break;
    case sending:
        FD_SET(m_sock, wfds);
        break;
    case readingLine:
        FD_SET(m_sock, rfds);
        break;
    case recievingBuf:
        FD_SET(m_sock, rfds);
        break;
    }
    return 0;
}

int CTcpSock::checkFdSets(fd_set* rfds, fd_set* wfds, fd_set* efds)
{
    int event = 0;
    if(FD_ISSET(m_sock, rfds)) event |= read;
    if(FD_ISSET(m_sock, wfds)) event |= write;
    if(FD_ISSET(m_sock, efds)) event |= except;
    if(event != 0)
        processEvent(event);
    // process internal events
    while(m_intStatus != noEvent)
    {
        int theEvent = m_intStatus;
        m_intStatus = noEvent;
        switch(theEvent)
        {
        case connectOk:
            if(m_cbConnectOk)
                (*m_cbConnectOk)(this);
            break;
        case sendOk:
            if(m_cbSendOk)
                (*m_cbSendOk)(this);
            break;
        case readLineOk:
            if(m_cbReadLineOk)
                (*m_cbReadLineOk)(this);
            break;
        case recvBufOk:
            if(m_cbRecvBufOk)
                (*m_cbRecvBufOk)(this);
            break;
        }

        if(m_intStatus == deleteEvent)
        {
            delete this;
            return 0;
        }
    }
    return 0;
};
    
int CTcpSock::processEvent(int event)
{
    switch(m_state)
    {
    case connecting:
        if(event & except)
        {
            tracef("connect FAILED\n");
            m_state = created;
            // TODO: make callback
            break;
        }
        if(event & write)
        {
	    int res;
	    int len = sizeof(res);
	    getsockopt(m_sock, SOL_SOCKET, SO_ERROR, (char *) &res, (socklen_t*) &len);
	    if(res == 0)
	    {
		tracef("connect OK\n");
		m_state = ready;
		m_intStatus = connectOk;
	    }
	    else
	    {
		tracef("connect FAILED\n");
		m_state = created;
		// TODO: make callback
	    }
        }
        break;
    case sending:
        if(event & except)
        {
            tracef("send FAILED\n");
            m_state = ready;
            // TODO: make callback
            break;
        }
        if(event & write)
        {
            tracef("send ... \n");
            if(m_sent < m_wlen)
            {
                int res;
                res = ::send(m_sock, &m_wbuf[m_sent], m_wlen - m_sent, 0);
                if(res >= 0)
                {
                    m_sent += res;
                }
                else
                {
                    // TODO: handle send error
                }
                if(m_sent == m_wlen)
                {
                    tracef("send DONE OK\n");
                    m_state = ready;
                    m_intStatus = sendOk;
                }
            }
        }
        break;
    case readingLine:
        if(event & except)
        {
            tracef("read FAILED");
            m_state = ready;
            // TODO: make callback
            break;
        }
        if(event & read)
        {
            readLineLoop();
        }
        break;
    case recievingBuf:
        if(event & except)
        {
            tracef("recv FAILED");
            m_state = ready;
            // TODO: make callback
            break;
        }
        if(event & read)
        {
            recvBufLoop();
        }
        break;
    };
    return 0;
}

void CTcpSock::deleteSock(void)
{
    close();
    m_intStatus = deleteEvent;
}

/* ------------------------------------------- */

