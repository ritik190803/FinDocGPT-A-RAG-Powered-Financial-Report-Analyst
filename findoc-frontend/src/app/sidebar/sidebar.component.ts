import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.css']
})
export class SidebarComponent {
  @Input() sessionModel: string = 'Llama 3.3 70B';
  @Input() vectorDb: string = 'ChromaDB';
  @Input() responseTime: string = '0.00 s';
  
  // Inputs for session data
  @Input() sessions: any[] = [];
  @Input() activeSessionId: string | null = null;

  // Outputs renamed to avoid native DOM event naming conflicts
  @Output() newChat = new EventEmitter<void>();
  @Output() selectSession = new EventEmitter<string>();
  @Output() deleteSessionEvent = new EventEmitter<string>();
  @Output() clearHistoryEvent = new EventEmitter<void>();

  startNewChat() {
    this.newChat.emit();
  }

  loadSession(id: string) {
    this.selectSession.emit(id);
  }

  onDeleteSession(event: Event, id: string) {
    // This stops the click from "bubbling up" and selecting the chat
    event.stopPropagation();
    this.deleteSessionEvent.emit(id);
  }

  clearHistory() {
    this.clearHistoryEvent.emit();
  }
}