import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppGate } from "./components/AppGate";
import { Fridge } from "./pages/Fridge";
import { Home } from "./pages/Home";
import { MealPlanHistory } from "./pages/MealPlanHistory";
import { MealPlanPage } from "./pages/MealPlanPage";
import { Onboarding } from "./pages/Onboarding";
import { Settings } from "./pages/Settings";
import { Unlock } from "./pages/Unlock";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/unlock" element={<Unlock />} />
        <Route
          path="/"
          element={
            <AppGate>
              <Home />
            </AppGate>
          }
        />
        <Route
          path="/plan/:id"
          element={
            <AppGate>
              <MealPlanPage />
            </AppGate>
          }
        />
        <Route
          path="/fridge"
          element={
            <AppGate>
              <Fridge />
            </AppGate>
          }
        />
        <Route
          path="/history"
          element={
            <AppGate>
              <MealPlanHistory />
            </AppGate>
          }
        />
        <Route
          path="/settings"
          element={
            <AppGate>
              <Settings />
            </AppGate>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
