import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-chat-input',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat-input.component.html',
  styleUrls: ['./chat-input.component.css']
})
export class ChatInputComponent {
  question: string = '';
  @Input() isLoading: boolean = false;
  @Output() sendQuestion = new EventEmitter<string>();

  onSubmit() {
    if (!this.question.trim() || this.isLoading) return;
    this.sendQuestion.emit(this.question);
    this.question = ''; // Clear input instantly
  }
}