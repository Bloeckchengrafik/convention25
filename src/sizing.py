from math import pi

def get_gear_ratio(teeth_on_motor: int, teeth_on_sink: int) -> float:
    if teeth_on_sink == 0 or teeth_on_motor == 0:
        raise ValueError("Number of teeth cannot be zero.")
    return teeth_on_motor / teeth_on_sink

worm_module = 1.5
worm_lead = worm_module * pi

class Distance:
    mm: int
    
    def __init__(self, cm: float = 0, mm: int = 0):
        cm_in_mm = int(cm * 10)
        self.mm = cm_in_mm + mm
        
    def to_steps(self, gear_ratio: float, steps_per_rotation: int = 200) -> int:
        """
        Convert the distance to motor steps.
        
        Used conversion:
        - MM -> Wormscrew rotations
        - Wormscrew rotations -> Axis rotations
        - Axis rotations -> Motor steps

        Args:
            gear_ratio (float): The gear ratio of the system.
            steps_per_rotation (int, optional): The number of steps per motor rotation. Defaults to 200.

        Returns:
            int: The number of motor steps required to move the specified distance.
        """
        return int((self.mm / worm_lead) * steps_per_rotation * gear_ratio)