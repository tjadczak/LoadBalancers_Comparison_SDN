/***************************************************************************
                          tmplchunk.cpp  -  description
                             -------------------
    begin                : Mon Jun 25 2001
    copyright            : (C) 2001 by pelle
    email                : pelle@localhost.localdomain
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/

#include "tmplchunk.h"
#include <stdlib.h>
#include <stdio.h>

CTmplChunk::CTmplChunk()
{
    m_pNext = NULL;
}

CTmplChunk::~CTmplChunk()
{
    // delete the rest of the list
    delete m_pNext;
}

/** Appends this chunk to the end of the list with the given start and end vars */
void CTmplChunk::Append(CTmplChunk*& pStart, CTmplChunk*& pEnd)
{
    if(pEnd == NULL)
    {
        // this is the first entry
        pStart = this;
    }
    else
    {
        // this is not the first entry
        pEnd->m_pNext = this;
    }
    pEnd = this;
}

/** verifies this chunk against the data given by pos and parm.
 *  pos is incremented by the length of the chunk */
int CTmplChunk::Verify(const char*& pos, const char* parm)
{
    return 0;
}
/** dump the chunk list */
void CTmplChunk::Dump()
{
    if(m_pNext)
        m_pNext->Dump();
}
