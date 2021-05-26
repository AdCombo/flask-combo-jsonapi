import os
import importlib
import logging
from http import HTTPStatus

import requests
import simplejson

logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger(__name__)

SNIPPETS_DIR = "snippets"
SORT_KEYS_ON_DUMP = True
SNIPPET_RESULT_POSTFIX = "_result"
REMOVE_PYTHON_SNIPPET = True


def run_request_for_module(module_name: str):
    log.info("Start processing %r", module_name)

    module_full_name = ".".join((SNIPPETS_DIR, module_name))
    log.debug("import module %s", module_full_name)
    module = importlib.import_module(module_full_name)

    log.info("Process module %s", module)
    response: requests.Response = module.response
    log.info("Response %s", response)
    http_response_text = []
    response_reason = (response.reason or "").title()
    http_response_text.append(
        # "HTTP/1.1 201 Created"
        "{} {} {}".format(
            "HTTP/1.1",
            response.status_code,
            response_reason,
        )
    )
    http_response_text.append(
        "{}: {}".format(
            "Content-Type",
            response.headers.get('content-type'),
        )
    )
    http_response_text.append("")

    http_response_text.append(
        simplejson.dumps(
            response.json(),
            sort_keys=SORT_KEYS_ON_DUMP,
            indent=2,
        ),
    )

    http_response_text.append("")

    result_text = "\n".join(http_response_text)
    log.debug("Result text:\n%s", result_text)

    result_file_name = "/".join((SNIPPETS_DIR, module_name + SNIPPET_RESULT_POSTFIX))
    with open(result_file_name, "w") as f:
        res = f.write(result_text)
        log.info("Wrote text (%s) to %r", res, result_file_name)

    log.info("Processed %r", module_name)


def main():
    log.warning("Starting")

    for module_name in os.listdir(SNIPPETS_DIR):
        if module_name.endswith(".py"):
            try:
                run_request_for_module(module_name[:-3])
            except Exception:
                log.exception("Could not process module %r, skipping", module_name)
            else:
                if REMOVE_PYTHON_SNIPPET:
                    os.unlink("/".join((SNIPPETS_DIR, module_name)))

    log.warning("Done")


if __name__ == "__main__":
    main()
