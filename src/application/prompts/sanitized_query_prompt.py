# Copyright (C) 2025 Veel Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

class SanitizedQueryPrompt:
    SANITIZED_QUERY_PROMPT_TEMPLATE = """
You are given a list of short user search queries that are variations on a theme. 
Produce a single, concise representative search phrase of no more than {max_words} words
that captures the intent of the examples. Return only the phrase (no explanation).

Your response must be in strict JSON format.
"""