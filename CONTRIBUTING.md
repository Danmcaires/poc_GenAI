# Contributing to StarlingX Copilot

This page documents the contribution and development process for this repository.

## Git Workflow

At the core, the development model of this repository is greatly inspired by
existing models out there. The central repo holds two main branches with an
infinite lifetime:

- **main**
- **drop/N**

The main branch at origin should be familiar to every Git user.
Parallel to the master branch, another branch exists called drop/N, which are our
release branches.

Next to the main branches, our development model uses a variety of supporting
branches to aid parallel development between team members, ease tracking of
features, prepare for production releases and to assist in quickly fixing live
production problems. Unlike the main branches, these branches always have a
limited life time, since they will be removed eventually.

The different types of branches we may use are:

- Staging branches
- Feature branches
- Fix branches

Each of these branches have a specific purpose and are bound to strict rules as
to which branches may be their originating branch and which branches must be
their merge targets.

Staging branches are used to develop new features for the upcoming or a distant
future release. When starting development of a feature, the target release in
which this feature will be incorporated may well be unknown at that point.
The essence of a staging branch is that it exists as long as the feature is in
development, but will eventually be merged back into the main (to definitely add
the new feature to the upcoming release) or discarded (in case of a disappointing
experiment).

### Staging branches

We consider the staging branches to be the main branch of development, where the
source code of HEAD always reflects a state with the latest delivered development
changes for the next release. Some would call this the “integration branch”.

When the source code in a staging branch reaches a stable point and is ready to be
released, all of the changes should be merged back into main somehow and then tagged
with a release number. How this is done in detail will be discussed further on.

### Feature branches

Feature branches (or sometimes called topic branches) are used to develop new features
for the upcoming or a distant future release. When starting development of a feature,
the target release in which this feature will be incorporated may well be unknown at
that point. The essence of a feature branch is that it exists as long as the feature
is in development, but will eventually be merged back into staging (to definitely add
the new feature to the upcoming release) or discarded (in case of a disappointing
experiment).

When starting work on a new feature, branch off from the staging branch of the feature
that you're working on.

```bash
git checkout staging/<NAME>
git pull
git branch --track feature/<FEATURE-NAME> staging/<NAME>
git checkout feature/<FEATURE-NAME>
```

Once you've finished your changes, push your branch to Github and open a pull request
for the staging branch.

### Fix branches

Fix branches are very much like release branches in that they are also meant to prepare
for a new production release, albeit unplanned. They arise from the necessity to act
upon an undesired state of a live production version.

```bash
git checkout staging/<NAME>
git pull
git branch --track fix/<FIX-NAME> staging/<NAME>
git checkout fix/<FIX-NAME>
```
