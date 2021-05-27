# Generate HTTP code snippets


## Install

```shell
# to use in cli
npm install --global httpsnippet
```

```shell
# to use as a module
npm install --save httpsnippet
```

## Spec

Create HAR specs (.json files) in this directory.

> **Don't edit any files in the `./snippets` directory manually!**

## Generate

### Create all snippets and run requests for them

```shell
# run and create for all minimal api requests
./run_and_create.sh minimal_api
```

```shell
# run and create for all nested api requests
./run_and_create.sh nested_api
```

```shell
# run and create for delete example nested api requests
./run_and_create.sh nested_api__delete
```

### Or do it manually:

```shell
# example
httpsnippet example.json --target node --client unirest --output ./snippets
```

```shell
# minimal api to python3
httpsnippet minimal_api__create_person.json --target python --client python3 --output ./snippets
```

```shell
# minimal api to http
httpsnippet minimal_api__create_person.json --target http --output ./snippets
```


```shell
# process multiple
httpsnippet ./*.json --target http --output ./snippets
```


### Create requests and run them, write results 

```shell
# create python-requests requests snippets
httpsnippet ./*.json --target python --client requests --output ./snippets
```

```shell
# Run requests for minimal api, save output
python3 update_snippets_with_responses.py minimal_api
```

```shell
# Run requests for nested api, save output
python3 update_snippets_with_responses.py nested_api
```

#### Verbose logs (DEBUG level)

```shell
# Run requests for nested api, save output
python3 update_snippets_with_responses.py nested_api --verbose
```

> **Pro tip:** run webserver for specs before running update_snippets_with_responses, otherwise it won't work 😉 


Copy-paste resulting help text (from between the "===" lines) to make includes.
