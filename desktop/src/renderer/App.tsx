import React from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { Chat } from "./pages/Chat";
import { Settings } from "./pages/Settings";

export function App(): React.ReactElement {
  return (
    <MemoryRouter initialEntries={["/chat"]}>
      <Routes>
        <Route path="/chat" element={<Chat />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </MemoryRouter>
  );
}
