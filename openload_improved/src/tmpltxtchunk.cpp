/***************************************************************************
                          tmpltxtchunk.cpp  -  description
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

#include "tmpltxtchunk.h"
#include <string.h>
#include <stdio.h>

CTmplTxtChunk::CTmplTxtChunk(const char* pos, long len)
{
    m_Pos = pos;
    m_Len = len;
}

CTmplTxtChunk::~CTmplTxtChunk()
{
}

/** Verifies this chunk by comparing against the text given by pos */
int CTmplTxtChunk::Verify(const char*& pos, const char* parm)
{
    if(strncmp(m_Pos, pos, m_Len) != 0)
    {
        // mismatch return false
        return 0;
    }
    else
    {
        // everything ok, update pos
        pos += m_Len;
        return 1;
    }
}
/** dump the text chunk */
void CTmplTxtChunk::Dump()
{
    printf("TEXT: pos 0x%p, len %ld\n[", m_Pos, m_Len);
    fwrite(m_Pos, m_Len, 1, stdout);
    printf("]\n");
    CTmplChunk::Dump();
}
