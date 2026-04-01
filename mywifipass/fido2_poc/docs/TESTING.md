# FIDO2 PoC - Testing and Execution

To validate the proper behavior of the FIDO2 implementation and endpoints, we have designed an automated testing suite inside `fido2_poc.tests`.

## Running the Tests
You can execute the FIDO2 endpoint unit tests by running the following command from within the Docker container context:

```bash
docker exec -e SSL=False mywifipass python manage.py test fido2_poc.tests -v 2
```

## Important Environment Note: `SSL=False`

It is **mandatory** to pass the `SSL=False` environment variable explicitly (or execute the test suite in an environment where `ssl = False` is set in `settings.py`). 

### Why is this necessary?
If the global `SSL` parameter is active, Django enables `SECURE_SSL_REDIRECT = True` via the Security Middleware. This will cause the internal testing client (which simulates plain HTTP requests without passing through Nginx/reverse proxy logic) to receive a `301 Moved Permanently` response redirecting to `https://testserver/...` long before it reaches the backend views and asserts logic. 

If you forget this flag, testing will fail prematurely citing a code mismatch:
`AssertionError: 301 != 200/400`.
