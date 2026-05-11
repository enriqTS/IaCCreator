import { useTourStore } from '@/store/tour-store';

describe('tour-store', () => {
  beforeEach(() => {
    useTourStore.setState({
      isActive: false,
      completed: false,
      currentStep: 0,
    });
    localStorage.clear();
  });

  it('starts with isActive=false, completed=false, currentStep=0', () => {
    const state = useTourStore.getState();
    expect(state.isActive).toBe(false);
    expect(state.completed).toBe(false);
    expect(state.currentStep).toBe(0);
  });

  describe('startTour', () => {
    it('sets isActive=true and currentStep=0', () => {
      useTourStore.setState({ isActive: false, currentStep: 3, completed: true });
      useTourStore.getState().startTour();

      const state = useTourStore.getState();
      expect(state.isActive).toBe(true);
      expect(state.currentStep).toBe(0);
    });
  });

  describe('nextStep', () => {
    it('advances currentStep by 1', () => {
      useTourStore.setState({ currentStep: 0 });
      useTourStore.getState().nextStep();
      expect(useTourStore.getState().currentStep).toBe(1);
    });

    it('clamps to max step index (3)', () => {
      useTourStore.setState({ currentStep: 3 });
      useTourStore.getState().nextStep();
      expect(useTourStore.getState().currentStep).toBe(3);
    });

    it('does not exceed bounds when called multiple times from last step', () => {
      useTourStore.setState({ currentStep: 3 });
      useTourStore.getState().nextStep();
      useTourStore.getState().nextStep();
      useTourStore.getState().nextStep();
      expect(useTourStore.getState().currentStep).toBe(3);
    });
  });

  describe('prevStep', () => {
    it('decreases currentStep by 1', () => {
      useTourStore.setState({ currentStep: 2 });
      useTourStore.getState().prevStep();
      expect(useTourStore.getState().currentStep).toBe(1);
    });

    it('clamps to 0 on first step', () => {
      useTourStore.setState({ currentStep: 0 });
      useTourStore.getState().prevStep();
      expect(useTourStore.getState().currentStep).toBe(0);
    });

    it('does not go below 0 when called multiple times', () => {
      useTourStore.setState({ currentStep: 0 });
      useTourStore.getState().prevStep();
      useTourStore.getState().prevStep();
      useTourStore.getState().prevStep();
      expect(useTourStore.getState().currentStep).toBe(0);
    });
  });

  describe('completeTour', () => {
    it('sets isActive=false and completed=true', () => {
      useTourStore.setState({ isActive: true, currentStep: 2 });
      useTourStore.getState().completeTour();

      const state = useTourStore.getState();
      expect(state.isActive).toBe(false);
      expect(state.completed).toBe(true);
    });
  });

  describe('persistence', () => {
    it('only persists the completed flag', () => {
      useTourStore.setState({ isActive: true, currentStep: 3, completed: true });

      const stored = JSON.parse(
        localStorage.getItem('diagram-editor:tour-state') || '{}',
      );
      expect(stored.state).toEqual({ completed: true });
    });
  });
});
