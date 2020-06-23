/***************************************************************************
                          tmplparmchunk.cpp  -  description
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

#include "tmplparmchunk.h"
#include <string.h>
#include <stdio.h>

CTmplParmChunk::CTmplParmChunk()
{
}

CTmplParmChunk::~CTmplParmChunk()
{
}

/** compares that the parm is present at pos */
int CTmplParmChunk::Verify(const char*& pos, const char* parm)
{
    if(strncmp(parm, pos, strlen(parm)) != 0)
    {
        // mismatch return false
        return 0;
    }
    else
    {
        // everything ok, update pos
        pos += strlen(parm);
        return 1;
    }
}
/** dump the param chunk */
void CTmplParmChunk::Dump()
{
    printf("PARM\n");
    CTmplChunk::Dump();
}
