"""
Created on 2022-09-11

@author: wf
"""

from dataclasses import dataclass

import ceurws


@dataclass
class Version:
    """
    Version handling for VolumeBrowser
    """

    name = "CEUR-WS Volume Browser"
    version = ceurws.__version__
    date = "2022-08-14"
    updated = "2024-03-13"
    description = "CEUR-WS Volume browser"

    authors = "Tim Holzheim, Wolfgang Fahl"

    doc_url = "https://wiki.bitplan.com/index.php/pyCEURmake"
    chat_url = "https://github.com/WolfgangFahl/pyCEURmake/discussions"
    cm_url = "https://github.com/WolfgangFahl/pyCEURmake"

    license = """Copyright 2022 contributors. All rights reserved.

  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied."""
    longDescription = f"""{name} version {version}
{description}

  Created by {authors} on {date} last updated {updated}"""
