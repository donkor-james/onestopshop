def is_palindrome(s):
    s = s.lower()
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True


def max_area(nums):
    left, right = 0, len(nums) - 1
    best = 0

    while left < right:
        width = right - left
        current_area = min(nums[left], nums[right]) * width
        best = max(best, current_area)

        if nums[left] < nums[right]:
            left += 1
        else:
            right -= 1

    return best


heights = [2, 3, 10, 5, 7, 8]

area = max_area(heights)
print(area)


# def soln(arr):
#     arr.sort()
#     result = []

#     for i in range(len(arr)):
#         target = arr[i]

#         left, right = i + 1, len(arr) - 1

#         while left < right:
#             current_sum = arr[left] + arr[right]

#             if current_sum + target == 0:
#                 result.append([target, arr[left], arr[right]])
#                 left += 1
#                 right -= 1
#             elif current_sum < target:
#                 left += 1
#             else:
#                 right -= 1

#     return result


# arr = [-3, -2, -1, 0, 1, 2, 3]
# print(soln(arr))


# def soln(word1, word2):
#     store1, store2 = {}

#     for char in word1:
#         store1[char] = store1.get(char, 0) + 1

#     for char in word2:
#         store2[char] = store2.get(char, 0) + 1

#     return store1 == store2


# string1 = "anagram"
# string2 = "nagaram"
# print(soln(string1, string2))


# def soln(word):
#     if len(word) == 1:
#         return word
#     return soln(word[1:]) + word[0]


# print(soln('a'))


# def soln(arr1, arr2):
#     result = {}
#     common = []

#     for i in arr1:
#         result[i] = result.get(i, 0) + 1

#     for i in arr2:
#         if result.get(i):
#             common.append(i)

#     return common


# arr1 = [0, 1, 2]
# arr2 = [0, 3]
# print(soln(arr1, arr2))


# def soln(arr):
#     seen = {}

#     for i in arr:
#         if i in seen:
#             return True
#         seen[i] = seen.get(i, 0) + 1

#     return False


# nums = [3, 3]
# print(soln(nums))


# def soln(nums):
#     nums.sort()
#     left, right = 0, len(nums) - 1
#     best = nums[left] * nums[left+1]

#     while left < right:
#         product = nums[left] * nums[right]
#         best = max(product, best)

#         if nums[left] < nums[right]:
#             left += 1
#         else:
#             right -= 1

#     return best


# nums = [-4, 1, 2]
# print(soln(nums))


def soln(nums):

    big = 0
    store = [big]
    nums.sort()

    for i in nums:
        if i > big:
            new_big = i
        if store[-1] < big:
            store.append(big)
        big = new_big
        print(store)
    if store[-1] < big:
        store.append(big)
    return store[-2]


nums = [5, 5, 4, 4, 8]
# print(list(set(nums)))


def soln(arr):
    left, right = 0, len(arr) - 1
    dict_1 = {}

    while left < right:
        dict_1["left"] = dict_1.get(left, '') + s[left]
        dict_1["right"] = dict_1.get(right, '') + s[right]
        left += 1
        right -= 1

    if dict_1["left"] == dict_1["right"]:
        return True
    else:
        return False


s = "(())[]"
# print(soln(s))


def soln_3(nums):
    nums.sort()
    sequence = set(nums)
    biggest = 0

    for i in sequence:
        streak = 0
        while i in sequence:
            i -= 1
            streak += 1

        biggest = max(streak, biggest)

    return biggest


nums = [0, 3, 7, 2, 5, 8, 4, 6, 0, 1, 10]
# print(soln_3(nums))


def soln_4(nums):
    nums.sort()
    left, right = 0, len(nums) - 1
    arr = []
    while left < right:
        result = nums[left] + nums[right]
        if result == 0:
            arr.append((nums[left], nums[right]))
            left += 1
            right -= 1
        elif result > 0:
            right -= 1
        else:
            left += 1

    return arr


nums = [-1, 0, 1]
# print(soln_4(nums))


def soln_2(words):
    store = {}

    for word in words:
        key = "".join(sorted(word))  # sort letters → common key
        if key not in store:
            store[key] = []
        store[key].append(word)
        print(store)

    return list(store.values())


# print(soln_2(["eat", "tea", "tan", "ate", "nat", "bat"]))
# [["eat", "tea", "ate"], ["tan", "nat"], ["bat"]]


# def func(s):
#     substring = set('')
#     groups = {}
#     new_substring = ''

#     for char in s:
#         if char not in substring:
#             new_substring += char
#             substring.add(char)

#             # if char not in substring:
#             #     substring.a(char)


def substring(s, k):
    left = 0
    sub_counter = {}
    max_len = 0

    for right in range(len(s)):
        sub_counter[s[right]] = sub_counter.get(s[right], 0) + 1

        while len(sub_counter) > k:
            sub_counter[s[left]] -= 1
            if sub_counter[s[left]] == 0:
                del sub_counter[s[left]]
            left += 1
        max_len = max(max_len, right - left + 1)

    return max_len

print(substring("eceba", 3))