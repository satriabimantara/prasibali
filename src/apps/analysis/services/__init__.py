"""AI services for PrasiBali: model catalog, model loading, feature extraction and the analysis pipeline.

Tasks (i) character identification and (ii) alias clustering use the `balinese-nlp` package; task (iii) role
classification uses the thesis pickles in PRETRAINED_MODELS_DIR. The loading and feature-extraction logic mirrors
`scripts/prasibali_models.py` and `scripts/test_pretrained_pipeline.py`, which were verified against the real models.
"""
