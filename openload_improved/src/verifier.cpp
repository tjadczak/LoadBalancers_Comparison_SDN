/***************************************************************************
                          verifier.cpp  -  description
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

#include "verifier.h"
#include "tmpltxtchunk.h"
#include "tmplparmchunk.h"
#include <stdio.h>
#include <string.h>

CVerifier::CVerifier()
{
    m_pTemplate = NULL;
    m_pMagic = NULL;
    m_pStart = NULL;
    m_pEnd = NULL;
}

CVerifier::~CVerifier()
{
    delete [] m_pTemplate;
    delete [] m_pMagic;
    delete m_pStart; // recursive delete all chunks
}

/** Loads a template from a file, with magic value marked by szMagic */
int CVerifier::LoadTemplate(const char* filename, const char* szMagic)
{
    FILE* fp;
    unsigned long size;

    // delete existing template and magic
    delete [] m_pTemplate;
    m_pTemplate = NULL;
    delete [] m_pMagic;

    // copy new magic
    m_pMagic = new char[strlen(szMagic + 1)]; // +1 for zero term
    strcpy(m_pMagic, szMagic);

    // check if the file exists
    fp = fopen(filename, "r");
    if (fp == NULL)
        return -1; // unable to open file

    // get filesize
    fseek(fp, 0, SEEK_END);
    size = ftell(fp);
    fseek(fp, 0, SEEK_SET);

    // allocate space
    m_pTemplate = new char[size + 1]; // we zero terminate

    // read the data
    if(fread(m_pTemplate, 1, size, fp) != size)
    {
        // unable to read the whole file
        fclose(fp);
        delete [] m_pTemplate;
        m_pTemplate = NULL;
        return -1;
    }

    // zero terminate
    m_pTemplate[size] = 0;

    // close the file
    fclose(fp);

    // parse the template
    ParseChunks();

    return 0;
}

/** parses the template into chunks of text and params */
void CVerifier::ParseChunks()
{
    char* p1;
    char* p2;
    CTmplTxtChunk* pTxtChunk;
    CTmplParmChunk* pParmChunk;

    // delete previous chunk list
    delete m_pStart;
    m_pStart = NULL;
    m_pEnd = NULL;

    p1 = m_pTemplate;
    while(1)
    {
        p2 = strstr(p1, m_pMagic);

        if(p2 == NULL)
        {
            // no more magic, insert last text chunk and exit loop
            if(strlen(p1))
            {
                pTxtChunk = new CTmplTxtChunk(p1, strlen(p1));
                pTxtChunk->Append(m_pStart, m_pEnd);
            }
            break;
        }
        else
        {
            // found some magic
            // see if there was a text chunk first
            if(p2 > p1)
            {
                // insert text chunk
                pTxtChunk = new CTmplTxtChunk(p1, p2 - p1);
                pTxtChunk->Append(m_pStart, m_pEnd);
            }
            // insert param chunk
            pParmChunk = new CTmplParmChunk();
            pParmChunk->Append(m_pStart, m_pEnd);

            // update position
            p1 = p2 + strlen(m_pMagic);
        }
    }

    //m_pStart->Dump();

}
/** verify the data and parameter against the template */
int CVerifier::Verify(const char* szData, const char* szParam)
{
    int res = 0;
    CTmplChunk* pChunk = m_pStart;
    // loop through the chunks
    while(pChunk)
    {
        res = pChunk->Verify(szData, szParam);
        // exit if we found a mismatch
        if(res == 0)
            break;
        pChunk = pChunk->m_pNext;
    }
    return res;
}
