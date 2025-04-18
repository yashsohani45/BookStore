from books.models import Genre

def genre_list(request):
    """Return a dictionary containing all genres for use in templates."""
    return {'genres': Genre.objects.all()}