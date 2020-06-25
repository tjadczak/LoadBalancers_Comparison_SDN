#include "event_loop.h"
#include <stdio.h>

/*#ifdef WIN32

#include <conio.h>

int checkStdIn(void)
{
    if(kbhit())
        {
            char c;
            c = getch();
		    return 1;
        }
    return 0;
}

#else // WIN32

int checkStdIn(void)
{
    struct timeval tv;
    tv.tv_sec = 0;
    tv.tv_usec = 0;

    fd_set rfds;

    FD_ZERO(&rfds);
    FD_SET(STDIN_FILENO, &rfds);
    select(STDIN_FILENO + 1, &rfds, NULL, NULL, &tv);

    if(FD_ISSET(STDIN_FILENO, &rfds))
	{
	    char buf[128];
	    fgets(buf, sizeof(buf), stdin);
	    return 1;
	}

    return 0;
}

#endif // WIN32*/

class CSockList
{
public:
    CTcpSock* m_sock;
    CSockList* m_pNext;
};

CEventLoop::CEventLoop(void)
{
    m_sockList = NULL;
}

CEventLoop::~CEventLoop(void)
{
    CSockList* pCurrent = m_sockList;
    CSockList* pNext;
    while(pCurrent)
    {
        pNext = pCurrent->m_pNext;
        delete pCurrent;
        pCurrent = pNext;
    }
}

int CEventLoop::run(void)
{
    m_bContinue = 1;
    int res = 0;
    fd_set rfds;
    fd_set wfds;
    fd_set efds;

    struct timeval tv;

    unsigned int i;

    CSockList* pSock;
    CSockList* pNext;
    while(m_bContinue)
    {
        FD_ZERO(&rfds);
        FD_ZERO(&wfds);
        FD_ZERO(&efds);
        i = 0;
        pSock = m_sockList;
        while(pSock)
        {
            pSock->m_sock->setFdSets(&rfds, &wfds, &efds);
            if(pSock->m_sock->m_sock > i)
				i = pSock->m_sock->m_sock;
            pSock = pSock->m_pNext;
        }

        if(i == 0)
		{
            break;
		}
		
		tv.tv_sec = 0;
		tv.tv_usec = 200000L;
		//printf("calling select, n=%d ... ", i+1);
        res = select(i + 1, &rfds, &wfds, &efds, &tv);
		//printf("returns %d\n", res);
        pSock = m_sockList;
        while(pSock)
        {
            pNext = pSock->m_pNext;
            pSock->m_sock->checkFdSets(&rfds, &wfds, &efds);
            pSock = pNext;
        }

        if(res == -1)
            printf("Error %d\n", getSocketError());

		//if(checkStdIn())
		//{
			//fprintf(stderr, "Ignoring input\n");
			//break;
		//}
    }
    return res;
}

void CEventLoop::stop(void)
{
    m_bContinue = 0;
}

void CEventLoop::addSock(CTcpSock* sock)
{
    CSockList* pNew = new CSockList;
    pNew->m_pNext = m_sockList;
    pNew->m_sock = sock;
    m_sockList = pNew;
}

void CEventLoop::removeSock(CTcpSock* sock)
{
    CSockList* pCurrent = m_sockList;
    CSockList* pNext;
    CSockList* pPrev = NULL;
    while(pCurrent)
    {
        pNext = pCurrent->m_pNext;
        if(pCurrent->m_sock == sock)
        {
            if(pPrev)
            {
                pPrev->m_pNext = pNext;
            }
            else
            {
                m_sockList = pNext;
            }
            delete pCurrent;
            break;
        }
        pPrev = pCurrent;
        pCurrent = pNext;
    }
}


