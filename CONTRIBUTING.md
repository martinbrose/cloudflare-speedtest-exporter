# Contributing to Cloudflare Speedtest Exporter

Thank you for considering contributing to Cloudflare Speedtest Exporter! We appreciate your interest in helping us improve the project.

## Table of Contents

- [Introduction](#introduction)
- [Getting Started](#getting-started)
- [Contributing Guidelines](#contributing-guidelines)
- [Where do I go from here?](#where-do-i-go-from-here)
- [Fork & create a branch](#fork--create-a-branch)
- [Get the test suite running](#get-the-test-suite-running)
- [Implement your fix or feature](#implement-your-fix-or-feature)
- [Make a Pull request](#make-a-pull-request)
- [Keeping your Pull Request updates](#keeping-your-pull-request-up-to-date)
- [License](#license)

## Introduction

This document outlines the guidelines for contributing to the Cloudflare Speedtest Exporter project. It provides information on how you can get started, the contributing guidelines, code of conduct, and license.

## Getting Started

To get started with contributing to the project, follow these steps:

1. Fork the repository on GitHub.
2. Clone the forked repository to your local machine.
3. Install the necessary dependencies.
4. Make your changes or additions.
5. Test your changes to ensure they work as expected.
6. Commit your changes and push them to your forked repository.
7. Submit a pull request to the main repository.

## Contributing Guidelines

Please follow these guidelines when contributing to the project:

- Ensure your code follows the project's coding style and conventions.
- Write clear and concise commit messages.
- Include tests for any new functionality or bugfixes.
- Document any changes or additions in the project's documentation.

## Where do I go from here?

If you've noticed a bug or have a feature request, make one! It's generally best if you get confirmation of your bug or approval for your feature request this way before starting to code.

## Fork & create a branch

If this is something you think you can fix, then fork and create a branch with a descriptive name.

A good branch name would be (where issue #325 is the ticket you're working on):

```shell
git checkout -b 325-add-jitter-to-output
```

## Get the test suite running

Make sure you're using a venv with the Python version that matches the one used in the project. Install the development requirements:

```shell
pip install -r requirements.txt
```

## Implement your fix or feature

At this point, you're ready to make your changes! Feel free to ask for help; everyone is a beginner at first 😸

## Make a Pull request

After you have implemented your changes and tested them, it's time to submit a pull request. Here's how you can do it:

```shell
git remote add upstream git@github.com:original/cloudflare-speedtest-exporter.git
git checkout master
git pull upstream master
```

Then update your feature branch from your local copy of master, and push it!

```shell
git checkout 325-add-jitter-to-output
git rebase master
git push --set-upstream origin 325-add-jitter-to-output
```
Go to the repository and make a Pull Request. The PR text should be useful to someone reading it in the future. Explain the issue that your PR is solving and how you solved it.

## Keeping your Pull Request up to date

While your pull request is under review, you may need to make updates based on the feedback received. Here's how you can keep your pull request up to date:

```shell
git checkout 325-add-jitter-to-output
git pull --rebase upstream master
git push --force-with-lease 325-add-jitter-to-output
```

## License

Cloudflare Speedtest Exporter is licensed under the [GNU GENERAL PUBLIC LICENSE](LICENSE). By contributing to this project, you agree to license your contributions under the same license.

We appreciate your contributions and look forward to your involvement in the project!
