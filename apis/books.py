from __future__ import annotations

from .http import APIError, Param, PublicAPI

_OPEN_LIBRARY = "https://openlibrary.org"


class BookSearchAPI(PublicAPI):
    """Open Library book search. No key."""

    name = "book_search"
    category = "books"
    description = "Searches books by title, author or keywords and returns their authors and first publication year."
    params = (
        Param("query", "string", "Title, author or keywords, e.g. 'dune frank herbert'."),
        Param("limit", "integer", "Maximum number of books, 1 to 20 (optional, defaults to 5).", required=False, default=5),
    )
    example_call = {"query": "dune", "limit": 1}
    example_response = {
        "total_found": 48312,
        "books": [
            {
                "title": "Dune",
                "authors": ["Frank Herbert"],
                "first_publish_year": 1965,
                "edition_count": 155,
                "url": "https://openlibrary.org/works/OL893414W",
            }
        ],
    }
    mock_payload = {
        "numFound": 48312,
        "start": 0,
        "docs": [
            {
                "author_name": ["Frank Herbert"],
                "edition_count": 155,
                "first_publish_year": 1965,
                "key": "/works/OL893414W",
                "title": "Dune",
            }
        ],
    }

    def fetch(self, query, limit):
        return self.get_json(
            f"{_OPEN_LIBRARY}/search.json",
            params={
                "q": query,
                "limit": max(1, min(limit, 20)),
                "fields": "title,author_name,first_publish_year,key,edition_count",
            },
        )

    def parse(self, payload, query, limit):
        return {
            "total_found": payload.get("numFound", 0),
            "books": [
                {
                    "title": doc.get("title"),
                    "authors": doc.get("author_name", []),
                    "first_publish_year": doc.get("first_publish_year"),
                    "edition_count": doc.get("edition_count"),
                    "url": f"{_OPEN_LIBRARY}{doc['key']}",
                }
                for doc in payload.get("docs", [])[:limit]
            ],
        }


class BookByISBNAPI(PublicAPI):
    """Open Library edition lookup by ISBN. No key."""

    name = "book_by_isbn"
    category = "books"
    description = "Looks up a book edition by its ISBN number: title, authors, publisher, publish date and page count."
    params = (Param("isbn", "string", "ISBN-10 or ISBN-13, e.g. '9780441172719'."),)
    example_call = {"isbn": "9780441172719"}
    example_response = {
        "isbn": "9780441172719",
        "title": "Dune",
        "authors": ["Frank Herbert"],
        "publishers": ["Ace"],
        "publish_date": "2020",
        "pages": 896,
        "url": "http://openlibrary.org/books/OL59726263M/Dune",
    }
    mock_payload = {
        "ISBN:9780441172719": {
            "url": "http://openlibrary.org/books/OL59726263M/Dune",
            "key": "/books/OL59726263M",
            "title": "Dune",
            "authors": [{"url": "http://openlibrary.org/authors/OL79034A/Frank_Herbert", "name": "Frank Herbert"}],
            "number_of_pages": 896,
            "publishers": [{"name": "Ace"}],
            "publish_date": "2020",
        }
    }

    @staticmethod
    def _clean(isbn: str) -> str:
        return isbn.replace("-", "").replace(" ", "")

    def fetch(self, isbn):
        return self.get_json(
            f"{_OPEN_LIBRARY}/api/books",
            params={"bibkeys": f"ISBN:{self._clean(isbn)}", "format": "json", "jscmd": "data"},
        )

    def parse(self, payload, isbn):
        isbn = self._clean(isbn)
        book = payload.get(f"ISBN:{isbn}")
        if not book:
            raise APIError(f"No book found with ISBN '{isbn}'.")
        return {
            "isbn": isbn,
            "title": book.get("title"),
            "authors": [a["name"] for a in book.get("authors", [])],
            "publishers": [p["name"] for p in book.get("publishers", [])],
            "publish_date": book.get("publish_date"),
            "pages": book.get("number_of_pages"),
            "url": book.get("url"),
        }


class AuthorSearchAPI(PublicAPI):
    """Open Library author search. No key."""

    name = "author_search"
    category = "books"
    description = "Finds a writer or author by name: birth and death dates, best-known work and number of works."
    params = (Param("name", "string", "Author name, e.g. 'Ursula K. Le Guin'."),)
    example_call = {"name": "J. R. R. Tolkien"}
    example_response = {
        "name": "J.R.R. Tolkien",
        "birth_date": "3 January 1892",
        "death_date": "2 September 1973",
        "top_work": "The Hobbit",
        "work_count": 621,
        "url": "https://openlibrary.org/authors/OL26320A",
    }
    mock_payload = {
        "numFound": 2,
        "start": 0,
        "docs": [
            {
                "key": "OL26320A",
                "name": "J.R.R. Tolkien",
                "birth_date": "3 January 1892",
                "death_date": "2 September 1973",
                "top_work": "The Hobbit",
                "work_count": 621,
                "type": "author",
            }
        ],
    }

    def fetch(self, name):
        return self.get_json(f"{_OPEN_LIBRARY}/search/authors.json", params={"q": name, "limit": 5})

    def parse(self, payload, name):
        docs = payload.get("docs") or []
        if not docs:
            raise APIError(f"No author found matching '{name}'.")
        # The most prolific match is almost always the one meant.
        author = max(docs, key=lambda doc: doc.get("work_count", 0))
        return {
            "name": author["name"],
            "birth_date": author.get("birth_date"),
            "death_date": author.get("death_date"),
            "top_work": author.get("top_work"),
            "work_count": author.get("work_count"),
            "url": f"{_OPEN_LIBRARY}/authors/{author['key']}",
        }
