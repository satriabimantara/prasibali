# Deploy notes

Production deployment is completed in session 7. This file records what the AI models need from the server.

## Model files

| What | Where | Size |
|---|---|---|
| Thesis classifier pickles and label encoder | `PRETRAINED_MODELS_DIR` (`models/pretrained-models/`, mounted read-only) | about 150 MB in total |
| FastText bahasa Bali, 300 dimensions (feature TF5) | `PRETRAINED_MODELS_DIR/balinese-word-embedding/300_fasttext_model.bin` when present, otherwise Hugging Face `satriabimantara/balinese_pretrained_wordembedding` (`FastText/300_fasttext_model.bin`) cached in `HF_HOME` | 2.3 GB on disk, including `.wv.vectors_ngrams.npy` |
| SatuaNER and the other NER models | inside the `balinese-nlp` package | small |

The embedding file must be the one used to train the TF5 pickles: every TF5 estimator expects 300 features
(`n_features_in_`), and the app refuses an embedding with a different `vector_size`.

## Memory (measured on the development laptop, 3 Nov 2026)

`python src/manage.py warm_models` loads SatuaNER, the label encoder, the default classifier
(`m2-wordvector-tf5-svm`) and FastText in about 5 seconds when the files are local.

| State of one Python process | Working set | Committed memory |
|---|---|---|
| Django only | 44 MB | 35 MB |
| + SatuaNER and default classifier | 245 MB | 1.7 GB |
| + FastText 300 | 2.56 GB | 4.0 GB |

On the 8 GB VPS:

- Run Gunicorn with `--preload` and `ANALYSIS_WARM_ON_START=true`, so the models are loaded once before the
  workers fork. The read-only arrays are then shared copy-on-write.
- Start with 2 sync workers (balinese-nlp extractors are not thread-safe) and watch `docker stats`. If memory runs
  short, use 1 worker.
- `ANALYSIS_CLASSIFIER_CACHE_SIZE` (default 4) limits how many classifier pickles stay loaded. M1 TF4 files are
  about 48 MB each.

## Hugging Face cache

- `HF_HOME` must be a persistent Docker volume. The first `warm_models` run downloads the embedding when it is not
  in `PRETRAINED_MODELS_DIR`.
- After the cache is filled, set `HF_HUB_OFFLINE=1`. `BaliFastText` has no revision parameter, so the filled cache
  is what pins the file.
- `HF_TOKEN` is needed only if the repository becomes private. It is read by `huggingface_hub` from the environment.

## Writable folders

- `BALINESE_NLP_WORK_DIR`: folder for the `saved_file` directory that `RuleBasedSentenceGrouping` creates.
  It defaults to `<system temp>/prasibali/saved_file`. Nothing is written into it per request.
