import json
import time
import os

class Stream:
    def __init__(self):
        pass
    def read(self):
        raise NotImplementedError()
    def write(self, data):
        raise NotImplementedError()

START = "::START"
QUIT = "::QUIT"
NONE = "::NONE"

class StreamIn(Stream):
    def __init__(self):
        self.last_data = None

    def read(self) -> int:
        try:
            return input(">> ")
        except KeyboardInterrupt:
            return QUIT
        except EOFError:
            return QUIT
    def write(self, data):
        if data == self.last_data:
            return
        self.last_data = data

        #time.sleep(0.25)
        for ch in data:
            print(ch, end='', flush=True)
            #time.sleep(0.025)
        print()

def json_load(something):
    try:
        if isinstance(something, str):
            if os.path.isfile(something):
                with open(something, "r") as fp:
                    definition = json.load(fp)
            else:
                definition = json.loads(something)
        else:
            definition = json.load(something)
    except BaseException as e:
        raise RuntimeError(f"JsonLoader: Failed to load: {e}")
    return definition

INCLUDE = "::INCLUDE"

class TreeTalk:
    @staticmethod
    def json_recurse_include_fileonly(definition, inclusion):
        if not os.path.isfile(inclusion):
            raise RuntimeError(f"TreeTalk: Cannot find JSON: {inclusion}")
        obj = json_load(inclusion)
        TreeTalk.json_recurse_include(obj)
        definition = {**definition, **obj}
        return definition

    @staticmethod
    def json_recurse_include(definition):
        if INCLUDE not in definition:
            return definition

        # Include all json in a directory or a json file itself, does not need
        # to end with .json as it will get applied if needed.
        for inclusion in definition[INCLUDE]:
            assert isinstance(inclusion, str)
            if os.path.isdir(inclusion):
                for filename in os.listdir(inclusion):
                    assert isinstance(filename, str)
                    if filename.endswith(".json"):
                        filename = f"{inclusion}{os.sep}{filename}"
                        definition = TreeTalk.json_recurse_include_fileonly(definition, filename)
            else:
                if not inclusion.endswith(".json"):
                    inclusion += ".json"

                definition = TreeTalk.json_recurse_include_fileonly(definition, inclusion)
        return definition

    def __init__(self, stream: Stream, definition, default=START):
        self.stream = stream
        self.definition = json_load(definition)
        self.current: str = default

        self.definition = TreeTalk.json_recurse_include(self.definition)

    def walk_one(self):
        if self.current not in self.definition:
            raise RuntimeError(f"TreeTalk: Failed to find current node {self.current}")

        node = self.definition[self.current]
        if node["type"] == "directive":
            return self.resolve_directive(node["directive"])

        elif node["type"] == "dialogue":
            for dialogue in node["dialogue"]:
                if not TreeTalk.is_directive(dialogue):
                    self.stream.write(dialogue)
                else:
                    return self.resolve_directive(dialogue)

        elif node["type"] == "msg":
            msg = node["msg"]
            opt = node["opt"]
            opt[QUIT] = QUIT
            opt[NONE] = NONE

            self.stream.write(msg)
            choice = self.stream.read()
            return self.resolve_directive(opt.get(choice, NONE))
        return False

    def walk(self):
        done = False
        while not done:
            done = self.walk_one()

    def resolve_directive(self, node: str):
        assert TreeTalk.is_directive(node)

        args = node.split()
        size = len(args)
        if 0 == size:
            raise RuntimeError(f"TreeTalk: Found a directive without args: {node}")
        elif 1 == size:
            if args[0] == "::QUIT":
                return True
            elif args[0] == "::NONE":
                return False
        elif 2 == size:
            if args[0] == "::GOTO":
                self.current = args[1]
            return False
        else:
            pass
        return False

    @staticmethod
    def is_directive(message: str):
        if isinstance(message, str):
            return message.startswith("::")
        return False

def usage():
    print("treetalk.py JSON_FILE")

def main():
    import sys
    if len(sys.argv) < 2:
        usage()
        return 1

    json_file = sys.argv[1]
    if not os.path.isfile(json_file):
        print(f"ERROR: Cannot find: {json_file}")
        usage()
        return 1

    tt = TreeTalk(StreamIn(), json_file)
    tt.walk()

    return 0

if __name__ == '__main__':
    exit(main())
