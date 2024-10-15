This `env-matrix` speeds up test execution across all environments (Python 3.[6,7,8],  Django2.0,...,3.1)

To execute

`docker-compose up --build`

First time it will take about half an hour (to install all)

Every other time it should take less than a minute to test across all environments.
