import { Component, ChangeDetectorRef, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatService, ChatResponse, SourceData } from './chat.service';
import { SidebarComponent } from './sidebar/sidebar.component'; // <-- Add Import
import { ChatInputComponent } from './chat-input/chat-input.component'; // <-- Add Import
import { marked } from 'marked';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  parsedContent?: string; 
  sources?: SourceData[];
  timestamp: Date;
  isLoading?: boolean;
  error?: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, SidebarComponent, ChatInputComponent], // <-- Register Here
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements AfterViewChecked {
  title = 'FinDocGPT Analyst';
  messages: ChatMessage[] = [];
  isLoading: boolean = false;

  sessionModel = 'Llama 3.3 70B';
  vectorDb = 'ChromaDB';
  responseTime = '0.00 s';

  @ViewChild('scrollWorkspace') private scrollWorkspace!: ElementRef;

  constructor(
    private chatService: ChatService,
    private cdr: ChangeDetectorRef
  ) {}

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  private scrollToBottom(): void {
    try {
      this.scrollWorkspace.nativeElement.scrollTop = this.scrollWorkspace.nativeElement.scrollHeight;
    } catch(err) { }
  }


// --- Phase 8: Theme Management ---
  isDarkMode: boolean = false;

  toggleTheme() {
    this.isDarkMode = !this.isDarkMode;
    if (this.isDarkMode) {
      document.body.classList.add('dark-theme');
    } else {
      document.body.classList.remove('dark-theme');
    }
  }

  handleNewQuestion(questionText: string) {
    this.isLoading = true;

    this.messages.push({
      role: 'user',
      content: questionText,
      timestamp: new Date()
    });

    const assistantMessage: ChatMessage = {
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true
    };
    this.messages.push(assistantMessage);
    this.cdr.detectChanges(); 

    const startTime = performance.now();

    this.chatService.askQuestion(questionText).subscribe({
      next: async (data: ChatResponse) => {
        assistantMessage.content = data.answer || '';
        assistantMessage.sources = data.sources || [];
        
        if (assistantMessage.content) {
          assistantMessage.parsedContent = await marked.parse(assistantMessage.content);
        }
        
        assistantMessage.isLoading = false;
        
        const endTime = performance.now();
        this.responseTime = ((endTime - startTime) / 1000).toFixed(2) + ' s';
        
        this.isLoading = false;
        this.cdr.detectChanges();
      },
      error: (err: any) => {
        assistantMessage.isLoading = false;
        assistantMessage.error = err.error?.detail || err.message || 'Failed to establish connection.';
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    });
  }

  viewSourceContext(source: SourceData) {
    alert(`Opening document viewer for ${source.company} FY${source.fiscal_year}, Page ${source.page_number}`);
  }

// --- Phase 7: Export Functions ---
  copyText(text: string) {
    navigator.clipboard.writeText(text).then(() => {
      // Simple alert for now, could be replaced with a toast notification later
      alert('Analysis copied to clipboard!'); 
    }).catch(err => console.error('Failed to copy: ', err));
  }

  downloadMarkdown(text: string) {
    const blob = new Blob([text], { type: 'text/markdown' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `FinDocGPT_Analysis_${new Date().getTime()}.md`;
    a.click();
    window.URL.revokeObjectURL(url);
  }

  downloadPDF() {
    alert('PDF Export UI connected! In a full production environment, this triggers a backend print service or uses a library like jsPDF.');
  }

  downloadDocx() {
    alert('DOCX Export UI connected! To generate native Word documents, this will link to your Python backend using the python-docx library.');
  }

}