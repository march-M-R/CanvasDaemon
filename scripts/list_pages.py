"""List every page, including paginated results; read-only."""
from pull_pages import check_env, get_all_pages


def main():
    check_env()
    pages = get_all_pages()
    print(f"Found {len(pages)} pages")
    for page in pages:
        print(f"{page['title']}\n  {page['url']}")


if __name__ == "__main__":
    main()
