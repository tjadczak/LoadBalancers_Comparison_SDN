/***************************************************************************
                          verifier.h  -  description
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

#ifndef VERIFIER_H
#define VERIFIER_H


#include "tmplchunk.h"

/**This class is used to verify
responses against a known
pattern
  *@author pelle
  */

class CVerifier
{
public: 
    CVerifier();
    ~CVerifier();
    /** Loads a template from a file, with magic value marked by szMagic */
    int LoadTemplate(const char* filename, const char* szMagic);
  /** verify the data and parameter against the template */
  int Verify(const char* szData, const char* szParam);
protected: // Protected attributes
    /** Holds the template data */
    char* m_pTemplate;
    /** Holds the magic string that identifies parameters in the template */
    char* m_pMagic;
    /** start of chunk list */
    CTmplChunk* m_pStart;
    /** end of chunk list */
    CTmplChunk* m_pEnd;
protected: // Protected methods
    /** parses the template into chunks of text and params */
    void ParseChunks();
};

#endif
