import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

// Strict typing aligning with our Pydantic models in FastAPI
export interface SourceData {
  company: string;
  fiscal_year: string;
  page_number: number;
  confidence?: number; // <-- Add this line
}

export interface ChatResponse {
  answer: string;
  sources: SourceData[];
}

@Injectable({
  providedIn: 'root'
})
export class ChatService {
  // Make sure to keep the /api/ask at the end!
private apiUrl = 'https://ritik1915-findoc-api.hf.space/api/ask';

  // Angular injects the HttpClient dependency here
  constructor(private http: HttpClient) {}

  askQuestion(question: string): Observable<any> {
  return this.http.post(this.apiUrl, { question });
}
}