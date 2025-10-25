# conduit - A modern, modular data-driven data pipeline for ML/AI

**conduit** is a modular data pipeline framework designed for creating, processing, and transforming datasets for machine learning (ML) and artificial intelligence (AI). Instead of writing brittle scripts that are buggy, hard to understand/modify, conduit allows users to compose pipelines from simple elements via `yaml` files. It removes the need for state machines and logic in data-processing scripts and makes them data-driven, externalizing and breaking down the steps needed to go from input to output, which can often be quite complex.

## Features

* **Data-driven** : By externalizing the composition stage of conventional data processing scripts, conduit effectively removes the need for a state machine in your data processing scripts which is typically the biggest source of bugs and code-rigidity.
* **Modular Design** : Build pipelines using composable`PipelineElement` components, including sources, transforms, sinks, and even sub-pipelines.
* **Lazy Evaluation** : Efficiently handle large datasets with support for iterable and generator-based processing.
* **Type-Safe** : Use Python's`typing` and`pydantic` models to enforce schema validation and type safety.
* **Hierarchical Pipelines** : Combine multiple pipelines into larger workflows with ease.
* **Customizable Components** : Quickly create your own data sources, transformations, or sinks to suit your needs.
* **Extensible for ML/AI** : Tailored for dataset preparation, augmentation, and integration into ML workflows. It's easy to write custom PipelineElements, which can then seamlessly integrate with other elements instead of having to rewrite/integrate an entire script from scratch.

## Installation

To install conduit into your own environment, you can simply use `pip`

```bash
pip3 install git+https://github.com/text2motion/conduit.git
```

## Development

This is a devcontainer-enabled repository, please see [here](https://code.visualstudio.com/docs/devcontainers/tutorial) for pre-requisites and installation steps.

Now you can simple open the this repository in VS Code and choose "Reopen in Container" from the popup.

## Usage

To use conduit, you can invoke it using a terminal after installation like so:

```sh
conduit-cli path/to/pipeline.yaml
```

See `launch.json` for an example of debugging your workflows.

If you are using this repository, there is no need for any setup. Just press F5 and choose from any of the listed workflows from the `examples` folder.

## Example yaml pipeline configuration

```yaml
---
- id: conduit.elements.Input
  pattern: '**/*.py'
  root_dir: .
  recursive: true
- id: conduit.elements.Glob
- id: conduit.elements.FileInfo
- id: conduit.elements.Console
```

The pipeline above is a simple example of finding a bunch of files and then printing their file information to the console. Now, if we wanted to run a CLI command against these files, we could just modify the same pipeline like so:

```yaml
---
- id: conduit.elements.Input
  pattern: '**/*.py'
  root_dir: .
  recursive: true
- id: conduit.elements.Glob
- id: conduit.elements.CliElement
  command: echo
  capture_output: true
  arguments: 
  - "************ {0} ************"
```

## Example pipeline element

It's easy to extend conduit to add your own pipeline elements that can do special things!

The below example shows how to define a simple pipeline element that can either create a new random float for each input, or create n number of random floats

```python
from typing import Generator, Iterator
from ..pipelineElement import PipelineElement

import random

class Random(PipelineElement):
    def __init__(self, seed: int = None, min: float = 0, max: float = 1, count: int = -1):
        self.seed = seed
        self.min = min
        self.max = max
        self.count = count

    def process(self, input: Iterator[None]) -> Generator[float, None, None]:
        if self.seed is not None:
            random.seed(self.seed)
        for _ in input if self.count == -1 else range(self.count):
            yield random.uniform(self.min, self.max)

```

Here, you can see that this is a subclass of `PipelineElement` and its `process` method accepts an `Iterator` and returns a `Generator`. This means that each element can iterate over items in the `input` and return a generator returning one or more items per input. Here, we see that if a `count` is specified, then the `process` method returns `count` random numbers. However, if `count` is not specified, it returns as many random numbers as there are items in the `input` iterator.

The corresponding pipeline to test this looks as follows:

```yaml

---
- id: conduit.elements.Input
- id: conduit.elements.Random
- id: conduit.elements.Console
  format: "{{input}}"
```

This will print exactly 1 random number because only a single input is specified as part of the pipeline. In other words, the `Random` pipeline element behaves like a "Transform" (albeit a one-way transform) on each input element (here, a single empty object).

```yaml
---
- id: conduit.elements.Random
  count: 10
- id: conduit.elements.Console
  format: "{{input}}"

```

This pipeline on the other hand, will print 10 random numbers since our `Random` pipeline element is now in "Generator" mode.
