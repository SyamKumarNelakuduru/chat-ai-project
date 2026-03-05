import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface AskRequest {
  question: string;
}

export interface AskResponse {
  answer: string;
  data_points?: number;
  query_type?: string;
}

@Injectable({
  providedIn: 'root'
})
export class AiService {
  private apiUrl = 'http://127.0.0.1:8000/api/ask';

  constructor(private http: HttpClient) {}

  askQuestion(question: string): Observable<AskResponse> {
    const request: AskRequest = { question };
    return this.http.post<AskResponse>(this.apiUrl, request);
  }
}
