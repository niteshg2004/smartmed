from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404

from .models import SearchHistory, Medicine
from .search import search_medicines


@login_required
def search_page(request):
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    dosage_form = request.GET.get("dosage_form", "").strip()
    
    results = []
    if query:
        # Note: Phase 2 search handles fuzzy search. We'll filter the results post-search if category/dosage_form are provided.
        # But wait, search_medicines returns MedicineSearchResult objects (which contain .medicine).
        raw_results = search_medicines(query, limit=50) # Get a few more to filter
        
        # Apply filters in Python memory since search_medicines might just do fuzzy matching.
        for r in raw_results:
            if category and r.medicine.therapeutic_category != category:
                continue
            if dosage_form and r.medicine.dosage_form != dosage_form:
                continue
            results.append(r)
            if len(results) >= 15:
                break
                
        if results and not category and not dosage_form: # Only log history for raw query searches
            SearchHistory.objects.create(
                user=request.user,
                medicine=results[0].medicine if results else None,
                query_text=query,
            )
            
    categories = Medicine.objects.exclude(therapeutic_category="").values_list('therapeutic_category', flat=True).distinct().order_by('therapeutic_category')
    dosage_forms = Medicine.DosageForm.choices

    context = {
        "query": query,
        "results": results,
        "category_filter": category,
        "dosage_form_filter": dosage_form,
        "categories": categories,
        "dosage_forms": dosage_forms,
    }
    return render(request, "medicines/search.html", context)


@login_required
def detail(request, id):
    medicine = get_object_or_404(Medicine, pk=id)
    return render(request, "medicines/detail.html", {"medicine": medicine})
