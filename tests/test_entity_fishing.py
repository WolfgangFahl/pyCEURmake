import unittest

import spacy
from spacy.cli import download

from ceurws.services.entity_fishing import ENTITY_FISHING_PIPELINE
from tests.basetest import Basetest, requires_entity_fishing_endpoint


class TestEntityFishing(Basetest):
    def setUp(self, debug=False, profile=True):
        super().setUp(debug=debug, profile=profile)
        try:
            nlp_lg = spacy.load("en_core_web_sm")
        except (OSError, ModuleNotFoundError):
            download(model="en_core_web_sm")
            nlp_lg = spacy.load("en_core_web_sm")
        self.nlp = nlp_lg

    @requires_entity_fishing_endpoint
    def test_entity_fishing_spacy_pipeline(self):
        """
        tests entity fishing spacy pipeline
        """
        text = (
            "University of Primorska, Faculty of Mathematics, Natural Sciences and Information Technologies, "
            "Koper, Slovenia, Stefan Decker"
        )
        nlp = spacy.load("en_core_web_sm")
        nlp.add_pipe(ENTITY_FISHING_PIPELINE)
        doc = nlp(text)
        entities = set()
        for ent in doc.ents:
            qid = ent._.kb_qid
            if qid:
                entities.add(qid)
            print(
                (
                    ent.text,
                    ent.label_,
                    ent._.kb_qid,
                    ent._.url_wikidata,
                    ent._.nerd_score,
                )
            )
        self.assertSetEqual(entities, {"Q1378123", "Q6431071", "Q215", "Q54303353"})


if __name__ == "__main__":
    unittest.main()
