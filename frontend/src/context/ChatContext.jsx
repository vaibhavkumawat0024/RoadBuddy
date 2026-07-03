import React, { createContext, useContext, useState, useCallback } from 'react';
import { tripsAPI } from '../api/client';

const ChatContext = createContext(null);

export const useChat = () => useContext(ChatContext);

export const ChatProvider = ({ children }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I am your AI RoadBuddy. Ask me to plan itineraries, calculate fuel costs, or find stops!' }
  ]);
  const [chatLoading, setChatLoading] = useState(false);

  const sendChatMessage = useCallback(async (text) => {
    if (!text.trim()) return;
    const userMsg = text.trim();
    
    // Add User message
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }]);
    setChatLoading(true);

    try {
      const history = messages.map(m => ({ role: m.role, content: m.content }));
      const res = await tripsAPI.chat(userMsg, history);
      const reply = res.data.reply || res.data.response || res.data.message || JSON.stringify(res.data);
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Failed to communicate with AI model.' }]);
    } finally {
      setChatLoading(false);
    }
  }, [messages]);

  return (
    <ChatContext.Provider
      value={{
        isOpen,
        setIsOpen,
        messages,
        setMessages,
        chatLoading,
        sendChatMessage
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};
