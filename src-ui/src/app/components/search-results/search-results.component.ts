import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { SearchService } from '../../services/search.service';
import { AnalyticsService } from '../../services/analytics.service';
import { SearchResponse, SearchResult, SearchFacets } from '../../models/search.model';

@Component({
  selector: 'app-search-results',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './search-results.component.html',
})
export class SearchResultsComponent implements OnInit {
  results = signal<SearchResult[]>([]);
  facets = signal<SearchFacets>({});
  totalCount = signal(0);
  loading = signal(false);
  query = signal('');
  currentPage = signal(1);
  pageSize = signal(25);

  constructor(
    private searchService: SearchService,
    private analyticsService: AnalyticsService,
    private route: ActivatedRoute,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.route.queryParams.subscribe((params) => {
      const q = params['q'] || '';
      const page = parseInt(params['page'] || '1', 10);
      this.query.set(q);
      this.currentPage.set(page);
      if (q) {
        this.doSearch();
      }
    });
  }

  doSearch(): void {
    this.loading.set(true);
    this.searchService
      .search({
        query: this.query(),
        page: this.currentPage(),
        page_size: this.pageSize(),
      })
      .subscribe({
        next: (res) => {
          this.results.set(res.results);
          this.facets.set(res.facets);
          this.totalCount.set(res.count);
          this.loading.set(false);
        },
        error: () => this.loading.set(false),
      });
  }

  onSearch(): void {
    this.currentPage.set(1);
    this.router.navigate(['/search'], {
      queryParams: { q: this.query(), page: 1 },
    });
  }

  goToPage(page: number): void {
    this.currentPage.set(page);
    this.router.navigate(['/search'], {
      queryParams: { q: this.query(), page },
    });
  }

  totalPages(): number {
    return Math.ceil(this.totalCount() / this.pageSize());
  }

  trackResultClick(result: SearchResult, position: number): void {
    this.analyticsService
      .trackClick({
        query: this.query(),
        document_id: result.id,
        position,
      })
      .subscribe();
  }
}
