import sublime, sublime_plugin
import pickle as pkl

# from http://stackoverflow.com/questions/2460177/edit-distance-in-python
def levenshteinDistance(s1, s2):
    if len(s1) > len(s2):
        s1, s2 = s2, s1

    distances = range(len(s1) + 1)
    for i2, c2 in enumerate(s2):
        distances_ = [i2+1]
        for i1, c1 in enumerate(s1):
            if c1 == c2:
                distances_.append(distances[i1])
            else:
                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
        distances = distances_
    return distances[-1]

class NGram(object):

    def __init__(self, corpus, n=2):
        def iterator(corpus, n):
            for i in range(len(corpus)):
                if i > n:
                    yield corpus[i], pkl.dumps(corpus[i-n:i])

        self.n = n
        self.data = {}
        for w, pre in iterator(corpus, n):
            if pre not in self.data:
                self.data[pre] = []
            self.data[pre].append(w)

    def __count_words(self, ll):
        result = {}
        for w in ll:
            if w not in result:
                result[w] = ll.count(w)
        return result


    def get(self, ll):
        key = pkl.dumps(ll)
        if key not in self.data:
            return {}
        return self.__count_words(self.data[key])

class NgramCommand(sublime_plugin.EventListener):

    def __load_corpus(self, path):
        with open(path,encoding="utf-8") as f:
            d = f.read()
            corpus = d.splitlines()
        return corpus

    def __init__(self):
        settings = sublime.load_settings('ngram_completion.sublime-settings')
        path = settings.get('path_to_corpus')
        highest_n = settings.get('highest_n')
        corpus = self.__load_corpus(path)
        self.models = [NGram(corpus, n+1) for n in range(highest_n)][::-1]

    def on_query_completions(self, view, prefix, locations):

        def get_substr_for_interval(a,b):
            region = sublime.Region(a, b)
            return view.substr(region)

        if len(locations) == 1:
            location = locations[0]

            # find n tokens before
            tokens = []
            c_char_before = 0
            c_word_is_unfinished = get_substr_for_interval(location-1, location) != " "

            while len(tokens) < max(map( lambda m: m.n, self.models)) + 1:

                max_iter = 100
                if c_char_before >= max_iter:
                    return []

                substr = get_substr_for_interval(location-c_char_before, location)

                c_char_before += 1
                tokens = [w for line in substr.split("\n") for w in line.split(" ") if w != ""]
            tokens = tokens[1:len(tokens)-int(c_word_is_unfinished)]
            c_unfinished_word = tokens[-1]

            # query ngram for matches
            matches = []
            for m in self.models:
                suggestions = m.get(tokens[-m.n:]).items()
                suggestions = sorted(suggestions, key=lambda x: x[1])

                for s,cnt in suggestions:
                    trigger = s
                    contents = s.replace('$', '\\$')
                    matches.append((trigger, contents))

            if c_word_is_unfinished:
                matches = sorted(matches, key= lambda x: levenshteinDistance(x, c_unfinished_word))

            return list(set(matches))